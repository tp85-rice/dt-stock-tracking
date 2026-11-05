"""Daily feeds job: run every signal's data feed and put new readings into the review queue.

    python -m worker.run_feeds              # all tickers
    python -m worker.run_feeds --ticker NVDA
    python -m worker.run_feeds --dry-run    # print what would be proposed; write nothing

Steps:
1. Apply feed settings from research/<TICKER>/feeds.json to the signals table (which adapter feeds which signal).
2. For each active signal with a feed (real tickers only), run the adapter.
3. For each reading, skip it if that signal and period already has an observation, or any proposal
   (pending, approved or rejected). Otherwise add the source to the ticker's source log if it is new and
   create a pending proposal with the quote and link. Nothing reaches the dashboard until a reviewer approves it.
4. Record the run (counts, errors) in the runs table.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import traceback
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb

from worker.adapters import Reading, registry

REPO = Path(__file__).resolve().parents[1]


def apply_feed_files(conn: psycopg.Connection, root: Path = REPO / "research") -> list[str]:
    """research/<TICKER>/feeds.json: {"signals": {"S7": {"adapter": "...", "params": {...}}, ...}}"""
    notes = []
    for path in sorted(root.glob("*/feeds.json")):
        ticker = path.parent.name.upper()
        cfg = json.loads(path.read_text())
        for code, feed in cfg.get("signals", {}).items():
            cur = conn.execute(
                "update signals set adapter = %s, adapter_params = %s where ticker = %s and code = %s",
                (feed["adapter"], Jsonb(feed.get("params", {})), ticker, code))
            if cur.rowcount == 0:
                notes.append(f"{path.relative_to(root.parent)}: {ticker} {code} is not in the database (import the sheet first)")
    return notes


def _exists(conn, ticker: str, signal: str, period: str) -> bool:
    return conn.execute(
        """select exists (select 1 from observations
                           where ticker = %(t)s and signal_code = %(s)s and lower(period) = lower(%(p)s))
               or exists (select 1 from proposals
                           where ticker = %(t)s and signal_code = %(s)s and kind = 'observation'
                             and lower(payload ->> 'period') = lower(%(p)s))""",
        {"t": ticker, "s": signal, "p": period}).fetchone()[0]


def _base_version(conn, ticker: str, signal: str) -> str:
    row = conn.execute(
        """select version from base_case where ticker = %s and signal_code = %s and case_type = 'Consensus'
           order by snapshot_date desc nulls last, id desc limit 1""", (ticker, signal)).fetchone()
    if row:
        return row[0]
    row = conn.execute("select version from base_case where ticker = %s order by snapshot_date desc nulls last, id desc limit 1",
                       (ticker,)).fetchone()
    return row[0] if row else "v1"


def _source_code(conn, ticker: str, r: Reading) -> str:
    row = conn.execute("select code from sources where ticker = %s and url = %s", (ticker, r.source_url)).fetchone()
    if row:
        return row[0]
    n = conn.execute(
        r"""select coalesce(max((substring(code from '^R(\d+)$'))::int), 0) + 1 from sources where ticker = %s""",
        (ticker,)).fetchone()[0]
    code = f"R{n}"
    conn.execute(
        """insert into sources (ticker, code, accessed_on, name, url, tier, access_method, cost, tos_note, redistribute,
                                reliability_note)
           values (%s, %s, %s, %s, %s, 'A', 'API', 'Free', 'Public SEC filing', 'Yes', 'Added by the daily feeds job')""",
        (ticker, code, dt.date.today(), r.title[:200], r.source_url))
    return code


def run(conn: psycopg.Connection, ticker: str | None = None, dry_run: bool = False,
        adapters: dict | None = None, feed_root: Path | None = None) -> dict:
    adapters = adapters if adapters is not None else registry()
    summary = {"proposed": [], "skipped": [], "errors": [], "notes": []}
    with conn.transaction():
        summary["notes"] = apply_feed_files(conn, feed_root or REPO / "research")
    signals = conn.execute(
        """select s.ticker, s.code, s.adapter, s.adapter_params from signals s join tickers t on t.symbol = s.ticker
           where s.adapter is not null and s.active and not t.is_test and (%s::text is null or s.ticker = %s)
           order by s.ticker, s.code""", (ticker, ticker)).fetchall()

    run_id = None
    if not dry_run:
        with conn.transaction():
            run_id = conn.execute("insert into runs (job, ticker) values ('feeds', %s) returning id", (ticker,)).fetchone()[0]

    for t, code, adapter, params in signals:
        fn = adapters.get(adapter)
        if fn is None:
            summary["errors"].append(f"{t} {code}: unknown adapter {adapter!r}")
            continue
        try:
            readings = fn(t, code, params or {})
        except Exception as exc:  # one broken feed must not stop the others
            summary["errors"].append(f"{t} {code} ({adapter}): {exc}")
            traceback.print_exc(file=sys.stderr)
            continue
        for r in readings:
            label = f"{t} {code} {r.period} = {r.value}"
            if _exists(conn, t, code, r.period):
                summary["skipped"].append(f"{label} (already recorded or reviewed)")
                continue
            if dry_run:
                summary["proposed"].append(label)
                continue
            with conn.transaction():
                conn.execute("select set_config('app.actor', 'run_feeds', true)")
                src = _source_code(conn, t, r)
                payload = {"observed_on": r.observed_on.isoformat(), "value": r.value, "period": r.period,
                           "base_case_version": _base_version(conn, t, code), "source_code": src}
                if r.notes:
                    payload["notes"] = r.notes
                conn.execute(
                    """insert into proposals (kind, ticker, signal_code, payload, citations, origin, run_id, check_result)
                       values ('observation', %s, %s, %s, %s, %s, %s, %s)""",
                    (t, code, Jsonb(payload), Jsonb([{"url": r.source_url, "quote": r.quote, "title": r.title}]),
                     adapter, run_id, Jsonb(r.check)))
            summary["proposed"].append(label)

    if not dry_run:
        with conn.transaction():
            conn.execute(
                """update runs set finished_at = now(), status = %s, n_proposals = %s, error = %s, meta = %s
                   where id = %s""",
                ("failed" if summary["errors"] and not summary["proposed"] and not summary["skipped"] else "succeeded",
                 len(summary["proposed"]), "\n".join(summary["errors"]) or None, Jsonb(summary), run_id))
    return summary


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Run data feeds and add new readings to the review queue.")
    ap.add_argument("--ticker")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    from worker.db import connect

    with connect() as conn:
        s = run(conn, ticker=args.ticker.upper() if args.ticker else None, dry_run=args.dry_run)
    for k in ("notes", "proposed", "skipped", "errors"):
        for line in s[k]:
            print(f"[{k.upper()}] {line}")
    print(f"\n{len(s['proposed'])} new proposal(s){' (dry run)' if args.dry_run else ''}, "
          f"{len(s['skipped'])} skipped, {len(s['errors'])} error(s).")
    return 1 if s["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
