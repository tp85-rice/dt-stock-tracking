"""Import a filled driver spreadsheet into the database.

Usage (from the repo root):

    python -m worker.import_xlsx inputs/NVDA_driver_sheet.xlsx --dry-run
    python -m worker.import_xlsx inputs/NVDA_driver_sheet.xlsx
    python -m worker.import_xlsx inputs/NVDA_driver_sheet.xlsx --ticker TEST --test

What it does, all in one transaction (all or nothing):

* tickers, sources, drivers, signals, event ladder: inserted or updated.
* base case: new rows inserted. Existing rows are never changed; if the sheet
  has a different value for an existing (version, case type, signal, period),
  the import stops and asks for a new version instead.
* scoring log: observations that came from an earlier import of this ticker are
  replaced. Observations approved in the app are never touched.
* rows that are in the database but no longer in the sheet are reported, not
  deleted.
"""

from __future__ import annotations

import argparse
import sys
from decimal import Decimal

import psycopg

from worker.driver_sheet import DriverSheet, parse


class SheetImportError(Exception):
    """Raised when the database rejects the sheet (e.g. a changed base case)."""


def _strip(rec: dict) -> dict:
    return {k: v for k, v in rec.items() if not k.startswith("_")}


def _upsert(cur, table: str, rows: list[dict], key: tuple[str, ...], ticker: str) -> None:
    for rec in rows:
        rec = {"ticker": ticker} | _strip(rec)
        cols = list(rec)
        updates = [c for c in cols if c not in key and c != "ticker"]
        sql = (
            f"insert into public.{table} ({', '.join(cols)}) "
            f"values ({', '.join('%(' + c + ')s' for c in cols)}) "
            f"on conflict (ticker, {', '.join(key)}) do "
            + (f"update set {', '.join(f'{c} = excluded.{c}' for c in updates)}" if updates else "nothing")
        )
        cur.execute(sql, rec)


def _report_missing(cur, table: str, column: str, ticker: str, in_sheet: set[str]) -> list[str]:
    cur.execute(f"select {column} from public.{table} where ticker = %s", (ticker,))
    return sorted(r[0] for r in cur.fetchall() if r[0] not in in_sheet)


def import_sheet(conn: psycopg.Connection, sheet: DriverSheet, is_test: bool = False,
                 actor: str = "import_xlsx") -> list[str]:
    """Write a validated sheet. Returns notes for the user. Raises SheetImportError."""
    if sheet.errors:
        raise SheetImportError(f"sheet has {len(sheet.errors)} errors; fix them first")
    t = sheet.ticker
    notes: list[str] = []

    with conn.transaction(), conn.cursor() as cur:
        cur.execute("select set_config('app.actor', %s, true)", (f"{actor}:{sheet.path.name}",))

        cur.execute("select is_test from public.tickers where symbol = %s", (t,))
        existing = cur.fetchone()
        if existing and existing[0] != is_test:
            raise SheetImportError(
                f"{t} already exists as a {'test' if existing[0] else 'real'} ticker; "
                f"{'add' if existing[0] else 'remove'} --test to import into it")
        cur.execute(
            """insert into public.tickers (symbol, archetype, owner_note, is_test)
               values (%s, %s, %s, %s)
               on conflict (symbol) do update
                 set archetype = excluded.archetype, owner_note = excluded.owner_note""",
            (t, sheet.archetype, sheet.owner_note, is_test))

        _upsert(cur, "sources", sheet.sources, ("code",), t)
        _upsert(cur, "drivers", sheet.drivers, ("code",), t)
        _upsert(cur, "signals", sheet.signals, ("code",), t)

        # Base case: append-only.
        conflicts = []
        for rec in sheet.base_case:
            cur.execute(
                """select value from public.base_case
                   where ticker = %s and lower(version) = lower(%s) and case_type = %s
                     and signal_code = %s and lower(period) = lower(%s)""",
                (t, rec["version"], rec["case_type"], rec["signal_code"], rec["period"]))
            row = cur.fetchone()
            if row is None:
                cur.execute(
                    """insert into public.base_case
                         (ticker, version, snapshot_date, case_type, signal_code, period, value,
                          unit, source_code, notes)
                       values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (t, rec["version"], rec["snapshot_date"], rec["case_type"], rec["signal_code"],
                     rec["period"], rec["value"], rec["unit"], rec["source_code"], rec["notes"]))
            elif Decimal(str(row[0])) != Decimal(str(rec["value"])):
                conflicts.append(
                    f"Base case row {rec['_row']}: {rec['signal_code']} {rec['version']} "
                    f"{rec['case_type']} {rec['period']} is already stored as {row[0]}, the sheet now "
                    f"says {rec['value']}. Base cases can't be changed: add it as a new version.")
        if conflicts:
            raise SheetImportError("\n".join(conflicts))

        _upsert(cur, "event_ladder", sheet.event_ladder, ("signal_code", "step_no"), t)

        cur.execute("delete from public.observations where ticker = %s and origin = 'import'", (t,))
        for rec in sheet.scores:
            cur.execute(
                """insert into public.observations
                     (ticker, signal_code, observed_on, value, base_case_version, period, arrow,
                      source_code, notes, withheld, origin)
                   values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'import')""",
                (t, rec["signal_code"], rec["observed_on"], rec["value"], rec["base_case_version"],
                 rec["period"], rec["arrow"], rec["source_code"], rec["notes"],
                 rec["withheld"] and rec["value"] is None))

        for table, column, items in (
            ("drivers", "code", sheet.drivers),
            ("signals", "code", sheet.signals),
            ("sources", "code", sheet.sources),
        ):
            gone = _report_missing(cur, table, column, t, {i["code"] for i in items})
            if gone:
                notes.append(f"In the database but not in the sheet ({table}): {', '.join(gone)}. "
                             "Left in place; delete them in the app if intended.")
    return notes


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("path", help="filled copy of templates/stock_driver_template.xlsx")
    ap.add_argument("--ticker", help="override the ticker in README!B2 (e.g. TEST for a dry run)")
    ap.add_argument("--test", action="store_true", help="mark the ticker as a test ticker (hidden from viewers)")
    ap.add_argument("--dry-run", action="store_true", help="check the sheet only; do not touch the database")
    ap.add_argument("--quiet", action="store_true", help="hide warnings")
    args = ap.parse_args(argv)

    # A trial import may load any sheet under a test ticker (e.g. --ticker TEST --test).
    sheet = parse(args.path, ticker_override=args.ticker, allow_rename=args.test)
    for issue in sheet.errors + ([] if args.quiet else sheet.warnings):
        print(issue)
    print(sheet.summary())
    if sheet.errors:
        print(f"\n{len(sheet.errors)} error(s): nothing was imported.")
        return 1
    if args.dry_run:
        print("\nDry run: the sheet is valid. Nothing was written.")
        return 0

    from worker.db import connect

    with connect() as conn:
        try:
            notes = import_sheet(conn, sheet, is_test=args.test)
        except SheetImportError as exc:
            print(f"\nImport stopped, nothing was written:\n{exc}")
            return 1
    for n in notes:
        print(n)
    print(f"\nImported {sheet.ticker}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
