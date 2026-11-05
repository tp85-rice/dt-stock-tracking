"""Quarterly financials for the ticker-page charts, read from SEC filings (inline XBRL).

    python -m worker.financials                 # every research/<TICKER>/financials.json
    python -m worker.financials --ticker NVDA
    python -m worker.financials --dry-run       # print, write nothing

Config, research/<TICKER>/financials.json:
    {"cik": 1045810, "fiscal_year_end_month": 1, "quarters": 8,
     "metrics": {"revenue": {"concept": "us-gaap:Revenues"},
                 "rev_data_center": {"concept": "us-gaap:Revenues", "dims": {"ProductOrServiceAxis": "DataCenterMember"}}}}

How a quarter is found, newest filing first (so restated figures win over older ones):
* a fact covering one quarter (80-100 days) in a 10-Q or 10-K;
* the fourth quarter, which companies report only inside the full year: 10-K annual figure minus the three
  quarters already found for that fiscal year.
Rows go to the financials table (one per ticker, metric, quarter end); the latest filing's figure replaces older ones.
These are reported facts, not judgments, so they bypass the review queue.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import psycopg

from worker import sec

REPO = Path(__file__).resolve().parents[1]


def fiscal_label(end: dt.date, fye_month: int) -> str:
    """'Q2 FY27' for a quarter ending 2026-07-26 when the fiscal year ends in January."""
    # Quarters end on the last weekend of a month (Jan 25, Jul 26) or, in 53-week years, early the next month
    # (Feb 1). Stepping back a week puts every quarter end inside its own month.
    e = end - dt.timedelta(days=7)
    m = e.month
    fy = e.year if m <= fye_month else e.year + 1
    if fye_month == 12:
        fy = e.year
    q = ((m - fye_month - 1) % 12) // 3 + 1
    return f"Q{q} FY{str(fy)[-2:]}" if fye_month != 12 else f"Q{q} CY{str(fy)[-2:]}"


def quarters_from_reports(reports: list[tuple[str, list[sec.Fact]]], metrics: dict, fye_month: int,
                          keep: int) -> list[dict]:
    """reports: [(source url, facts)] newest first. Returns rows for the newest `keep` quarters per metric."""
    direct: dict[tuple[str, dt.date], tuple[int, dict]] = {}     # reported quarter facts, newest filing first
    derived: dict[tuple[str, dt.date], tuple[int, dict]] = {}    # six-month figure minus the following quarter
    annual: dict[tuple[str, dt.date], tuple[float, str, dt.date]] = {}
    for rank, (url, facts) in enumerate(reports):
        for metric, spec in metrics.items():
            dims = spec.get("dims", {})
            mine = [f for f in facts if f.name == spec["concept"] and f.dims == dims and f.days]
            quarters = {f.end: f for f in mine if 80 <= f.days <= 100}
            for f in quarters.values():
                direct.setdefault((metric, f.end), (rank, {"metric": metric, "period_end": f.end,
                                                           "value": float(f.value), "source_ref": url}))
            # A six-month figure minus this filing's quarter gives the previous quarter on the SAME definition.
            # This is how restated (recast) earlier quarters reach the chart: the restatement is in the
            # year-to-date column of the newest filing, not in a separate quarter fact.
            for f in mine:
                if 170 <= f.days <= 190 and f.end in quarters:
                    q = quarters[f.end]
                    prev_end = q.start - dt.timedelta(days=1)
                    derived.setdefault((metric, prev_end), (rank, {"metric": metric, "period_end": prev_end,
                                                                   "value": float(f.value) - float(q.value),
                                                                   "source_ref": url, "derived": True}))
                elif 350 <= f.days <= 380:
                    annual.setdefault((metric, f.end), (float(f.value), url, f.start))
    # A derived figure wins only when it comes from a newer filing AND differs by more than rounding (0.1%):
    # that is a restatement. Otherwise keep the exact reported figure.
    out: dict[tuple[str, dt.date], dict] = {}
    for key in set(direct) | set(derived):
        d, v = direct.get(key), derived.get(key)
        if v and (d is None or (v[0] < d[0] and abs(v[1]["value"] - d[1]["value"]) > 0.001 * abs(d[1]["value"]))):
            out[key] = v[1]
        else:
            out[key] = d[1]
    # Fourth quarters: annual minus the fiscal year's first three quarters.
    for (metric, end), (total, url, start) in annual.items():
        if (metric, end) in out:
            continue
        q123 = [v for (m, e), v in out.items() if m == metric and start < e < end]
        if len(q123) == 3:
            out[(metric, end)] = {"metric": metric, "period_end": end,
                                  "value": total - sum(r["value"] for r in q123), "source_ref": url, "derived": True}
    rows = []
    for metric in metrics:
        mine = sorted((r for (m, _), r in out.items() if m == metric), key=lambda r: r["period_end"], reverse=True)
        for r in mine[:keep]:
            r["fiscal_period"] = fiscal_label(r["period_end"], fye_month)
            rows.append(r)
    return rows


def load(conn: psycopg.Connection | None, ticker: str, cfg: dict, dry_run: bool = False) -> list[dict]:
    cik = int(cfg["cik"])
    filings = sec.list_filings(cik, "10-Q", 7) + sec.list_filings(cik, "10-K", 2)
    filings.sort(key=lambda f: f.filed, reverse=True)
    if conn is not None and not dry_run and filings:
        newest = sec.primary_document(filings[0])
        if conn.execute("select 1 from financials where ticker = %s and source_ref = %s limit 1",
                        (ticker, newest)).fetchone():
            return []  # already loaded from the newest filing
    reports = []
    for f in filings:
        url = sec.primary_document(f)
        reports.append((url, sec.xbrl_facts(sec.fetch(url))))
    rows = quarters_from_reports(reports, cfg["metrics"], int(cfg.get("fiscal_year_end_month", 12)),
                                 int(cfg.get("quarters", 8)))
    if conn is not None and not dry_run:
        with conn.transaction():
            for r in rows:
                conn.execute(
                    """insert into financials (ticker, metric, period_end, fiscal_period, value, unit, source, source_ref)
                       values (%s, %s, %s, %s, %s, 'USD', 'edgar', %s)
                       on conflict (ticker, metric, period_end, source) do update
                         set value = excluded.value, fiscal_period = excluded.fiscal_period,
                             source_ref = excluded.source_ref, fetched_at = now()""",
                    (ticker, r["metric"], r["period_end"], r["fiscal_period"], r["value"], r["source_ref"]))
    return rows


def run(conn, ticker: str | None = None, dry_run: bool = False, root: Path = REPO / "research") -> dict:
    summary = {"loaded": {}, "errors": []}
    for path in sorted(root.glob("*/financials.json")):
        t = path.parent.name.upper()
        if ticker and t != ticker:
            continue
        try:
            rows = load(conn, t, json.loads(path.read_text()), dry_run)
            summary["loaded"][t] = len(rows)
        except Exception as exc:  # one ticker must not stop the others
            summary["errors"].append(f"{t}: {exc}")
    return summary


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Load quarterly financials from SEC filings for the charts.")
    ap.add_argument("--ticker")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    t = args.ticker.upper() if args.ticker else None
    if args.dry_run:
        for path in sorted((REPO / "research").glob("*/financials.json")):
            if t and path.parent.name.upper() != t:
                continue
            for r in load(None, path.parent.name.upper(), json.loads(path.read_text()), dry_run=True):
                print(f"{path.parent.name} {r['metric']:<20} {r['fiscal_period']:<8} {r['period_end']} {r['value']:>20,.0f}"
                      f"{' (derived)' if r.get('derived') else ''}")
        return 0
    from worker.db import connect

    with connect() as conn:
        s = run(conn, t)
    for k, n in s["loaded"].items():
        print(f"[LOADED] {k}: {n} rows" if n else f"[UP TO DATE] {k}")
    for e in s["errors"]:
        print(f"[ERROR] {e}")
    return 1 if s["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
