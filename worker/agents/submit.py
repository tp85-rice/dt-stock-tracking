"""Put agent answers into the review queue, the same queue the daily feeds use.

    python -m worker.agents.submit answers.jsonl --dry-run     # print what would go in; write nothing
    python -m worker.agents.submit answers.jsonl               # add them to /review

Rules (the same for every agent, so a new agent cannot skip them):
* Only signals that already exist for the ticker (owner-defined drivers only).
* Skip a reading if that signal and period already has an observation or any proposal.
* Run the quote check (checks.py). Passed -> 'pending' for a reviewer. Failed -> 'rejected_by_check', kept for
  the record with the reasons, never shown as pending.
* Each submission is one row in the runs table (job 'agent_submit'), with token use and cost when the answers
  carry 'usage'. Nothing reaches the dashboard until a reviewer approves it.
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys

import psycopg
from psycopg.types.json import Jsonb

from worker.agents import answers as answers_mod
from worker.agents.budget import Budget, BudgetExceeded
from worker.agents.checks import check
from worker.run_feeds import _base_version, _exists

ORIGIN = "agent_junior"
PAYLOAD_KEYS = ("observed_on", "value", "period", "arrow", "notes", "withheld")


def _source_code(conn, ticker: str, a: dict) -> str:
    row = conn.execute("select code from sources where ticker = %s and url = %s", (ticker, a["source_url"])).fetchone()
    if row:
        return row[0]
    n = conn.execute(r"""select coalesce(max((substring(code from '^R(\d+)$'))::int), 0) + 1 from sources
                         where ticker = %s""", (ticker,)).fetchone()[0]
    code = f"R{n}"
    conn.execute(
        """insert into sources (ticker, code, accessed_on, name, url, tier, access_method, cost, tos_note, redistribute,
                                reliability_note)
           values (%s, %s, %s, %s, %s, 'C', 'Scrape', 'Unknown', 'Added by an AI agent: check the terms', 'Unknown',
                   'Found by an AI agent; set the tier when approving')""",
        (ticker, code, dt.date.today(), (a.get("source_title") or a["source_url"])[:200], a["source_url"]))
    return code


def submit(conn: psycopg.Connection, items: list[dict], dry_run: bool = False, origin: str = ORIGIN) -> dict:
    out = {"proposed": [], "held_by_check": [], "skipped": [], "errors": []}
    budget = Budget(None if dry_run else conn)
    run_id = None
    if not dry_run:
        with conn.transaction():
            run_id = conn.execute("insert into runs (job) values ('agent_submit') returning id").fetchone()[0]
        budget.run_id = run_id

    for a in items:
        where = f"line {a.get('_line', '?')}" if isinstance(a, dict) else "?"
        probs = answers_mod.schema_problems(a, "submit")
        if probs:
            out["errors"].append(f"{where}: " + "; ".join(probs))
            continue
        t, code = a["ticker"].upper(), a["signal_code"]
        label = f"{t} {code} {a['period']} = {a.get('value')}"
        if conn.execute("select 1 from signals where ticker = %s and code = %s", (t, code)).fetchone() is None:
            out["errors"].append(f"{where}: {t} {code} is not a defined signal (agents only update owner-defined drivers)")
            continue
        if a.get("abstain"):
            out["skipped"].append(f"{label} (agent abstained)")
            continue
        if _exists(conn, t, code, a["period"]):
            out["skipped"].append(f"{label} (already recorded or reviewed)")
            continue
        result = check(a, a.get("source_text"))
        bucket = "proposed" if result["passed"] else "held_by_check"
        if dry_run:
            out[bucket].append(label + ("" if result["passed"] else f" ({'; '.join(result['reasons'])})"))
            continue
        try:
            with conn.transaction():
                conn.execute("select set_config('app.actor', %s, true)", (origin,))
                usage = a.get("usage") or {}
                if a.get("model") and usage:
                    budget.record(a["model"], usage.get("input_tokens", 0), usage.get("output_tokens", 0))
                payload = {k: a[k] for k in PAYLOAD_KEYS if a.get(k) is not None}
                payload["observed_on"] = str(a["observed_on"])
                payload["base_case_version"] = _base_version(conn, t, code)
                payload["source_code"] = _source_code(conn, t, a)
                conn.execute(
                    """insert into proposals (kind, ticker, signal_code, payload, citations, status, origin, run_id,
                                              prompt_version, model, confidence, check_result)
                       values ('observation', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (t, code, Jsonb(payload),
                     Jsonb([{"url": a["source_url"], "quote": a["quote"], "title": a.get("source_title")}]),
                     "pending" if result["passed"] else "rejected_by_check", origin, run_id,
                     a.get("prompt_version"), a.get("model"), a.get("confidence"), Jsonb(result)))
            out[bucket].append(label if result["passed"] else f"{label} ({'; '.join(result['reasons'])})")
        except (psycopg.Error, BudgetExceeded) as exc:
            out["errors"].append(f"{where}: {exc}")

    if not dry_run:
        with conn.transaction():
            conn.execute(
                "update runs set finished_at = now(), status = %s, n_proposals = %s, error = %s, meta = %s where id = %s",
                ("failed" if out["errors"] and not out["proposed"] else "succeeded", len(out["proposed"]),
                 "\n".join(out["errors"]) or None, Jsonb(out), run_id))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Add agent answers (JSON lines) to the review queue.")
    ap.add_argument("answers")
    ap.add_argument("--dry-run", action="store_true", help="print what would be proposed; write nothing")
    args = ap.parse_args(argv)
    from worker.db import connect

    items = answers_mod.load(args.answers)
    with connect() as conn:
        out = submit(conn, items, dry_run=args.dry_run)
    for k in ("proposed", "held_by_check", "skipped", "errors"):
        for line in out[k]:
            print(f"[{k.upper()}] {line}")
    print(f"\n{len(out['proposed'])} for review{' (dry run)' if args.dry_run else ''}, {len(out['held_by_check'])} held "
          f"by the quote check, {len(out['skipped'])} skipped, {len(out['errors'])} error(s).")
    return 1 if out["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
