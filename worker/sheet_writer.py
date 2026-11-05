"""Write a driver spreadsheet from a JSON spec.

Agents (and the driver-sheet-builder skill) never edit cells by hand. They
write a spec file, e.g. research/NVDA/driver_spec.json, and this turns it into
a filled copy of templates/stock_driver_template.xlsx, then checks it with the
same validator the importer uses:

    python -m worker.sheet_writer research/NVDA/driver_spec.json inputs/NVDA_driver_sheet.xlsx

Spec shape (every key optional except ticker; field names are the keys of COLUMNS):

    {
      "ticker": "NVDA", "archetype": "...", "owner_note": "Draft by agent, unreviewed 2026-11-04",
      "Drivers":      [{"code": "D1", "name": "...", "type": "Core", "share": 0.4, ...}],
      "Signals":      [{"code": "S1", "driver": "D1", "name": "...", "star": "Y", ...}],
      "Base case":    [{"version": "v1", "case_type": "Consensus", "signal": "S1", ...}],
      "Event ladder": [{"signal": "S6", "step": 1, "milestone": "...", "kind": "Disclosure", ...}],
      "Source log":   [{"code": "R1", "name": "...", "url": "...", ...}],
      "Scoring log":  [{"date": "2026-08-27", "signal": "S5", "value": 72.4, ...}]
    }

Dates may be written as "YYYY-MM-DD" strings; they are stored as real dates.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

import openpyxl

TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "stock_driver_template.xlsx"

# Input columns per tab (template v2). Formula columns are never written.
COLUMNS = {
    "Drivers": {"code": "A", "name": "B", "thesis": "C", "valuation": "D", "horizon": "E",
                "impact": "F", "direction": "G", "evidence": "H", "confidence": "I", "notes": "M",
                "type": "N", "share": "O", "depends_on": "P"},
    "Signals": {"code": "A", "driver": "B", "name": "C", "source": "D", "tier": "E", "cadence": "F",
                "unit": "G", "polarity": "H", "tolerance": "I", "staleness": "J", "reliability": "K",
                "definition_change": "L", "notes": "M",
                "star": "N", "kill_switch": "O", "anchor": "P"},
    "Base case": {"version": "A", "snapshot": "B", "case_type": "C", "signal": "D", "period": "E",
                  "value": "F", "unit": "G", "source": "H", "notes": "I"},
    "Event ladder": {"signal": "A", "step": "B", "milestone": "C", "target": "D", "status": "E",
                     "actual": "F", "source": "I", "notes": "J", "kind": "K"},
    "Source log": {"code": "A", "accessed": "B", "name": "C", "url": "D", "tier": "E", "access": "F",
                   "cost": "G", "tos": "H", "redistribute": "I", "used_for": "J", "reliability": "K"},
    "Scoring log": {"date": "A", "signal": "B", "value": "C", "version": "D", "period": "E",
                    "arrow": "M", "source": "N", "notes": "O", "withheld": "P"},
}
DATE_FIELDS = {"snapshot", "target", "actual", "accessed", "date"}
_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _cell_value(field: str, value):
    if field in DATE_FIELDS and isinstance(value, str) and _ISO.match(value):
        return dt.date.fromisoformat(value)
    return value


def write(spec: dict, out: Path, template: Path = TEMPLATE) -> Path:
    unknown_tabs = set(spec) - set(COLUMNS) - {"ticker", "archetype", "owner_note", "_comment"}
    if unknown_tabs:
        raise ValueError(f"unknown keys in spec: {sorted(unknown_tabs)}")
    wb = openpyxl.load_workbook(template)
    readme = wb["README"]
    readme["B2"] = spec.get("ticker")
    readme["B3"] = spec.get("archetype")
    readme["B4"] = spec.get("owner_note")
    for tab, cols in COLUMNS.items():
        ws = wb[tab]
        for i, row in enumerate(spec.get(tab, []), start=2):
            bad = set(row) - set(cols) - {"_comment"}
            if bad:
                raise ValueError(f"{tab} row {i}: unknown fields {sorted(bad)}; allowed: {sorted(cols)}")
            for field, value in row.items():
                if field != "_comment" and value is not None:
                    ws[f"{cols[field]}{i}"] = _cell_value(field, value)
    out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out)
    return out


def build(path: Path, ticker: str | None = "NVDA", **tabs: list[dict]) -> Path:
    """Test helper: build(path, Drivers=[...], Base_case=[...]) (underscores for spaces)."""
    spec = {"ticker": ticker} | {k.replace("_", " "): v for k, v in tabs.items()}
    return write(spec, Path(path))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Write a driver spreadsheet from a JSON spec, then check it.")
    ap.add_argument("spec", help="JSON spec, e.g. research/NVDA/driver_spec.json")
    ap.add_argument("out", help="xlsx to write, e.g. inputs/NVDA_driver_sheet.xlsx")
    args = ap.parse_args(argv)

    spec = json.loads(Path(args.spec).read_text())
    out = write(spec, Path(args.out))
    print(f"Wrote {out}")

    from worker.driver_sheet import parse

    sheet = parse(out)
    for issue in sheet.errors + sheet.warnings:
        print(issue)
    print(sheet.summary())
    return 1 if sheet.errors else 0


if __name__ == "__main__":
    sys.exit(main())
