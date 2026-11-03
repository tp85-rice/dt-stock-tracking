"""Build filled driver sheets for tests from the real template."""

from __future__ import annotations

from pathlib import Path

import openpyxl

TEMPLATE = Path(__file__).resolve().parents[2] / "templates" / "stock_driver_template.xlsx"

# Input columns per tab, in the template's order (formula columns are skipped).
COLUMNS = {
    "Drivers": {"code": "A", "name": "B", "thesis": "C", "valuation": "D", "horizon": "E",
                "impact": "F", "direction": "G", "evidence": "H", "confidence": "I", "notes": "M"},
    "Signals": {"code": "A", "driver": "B", "name": "C", "source": "D", "tier": "E", "cadence": "F",
                "unit": "G", "polarity": "H", "tolerance": "I", "staleness": "J", "reliability": "K",
                "definition_change": "L", "notes": "M"},
    "Base case": {"version": "A", "snapshot": "B", "case_type": "C", "signal": "D", "period": "E",
                  "value": "F", "unit": "G", "source": "H", "notes": "I"},
    "Event ladder": {"signal": "A", "step": "B", "milestone": "C", "target": "D", "status": "E",
                     "actual": "F", "source": "I", "notes": "J"},
    "Source log": {"code": "A", "accessed": "B", "name": "C", "url": "D", "tier": "E", "access": "F",
                   "cost": "G", "tos": "H", "redistribute": "I", "used_for": "J", "reliability": "K"},
    "Scoring log": {"date": "A", "signal": "B", "value": "C", "version": "D", "period": "E",
                    "arrow": "M", "source": "N", "notes": "O"},
}


def build(path: Path, ticker: str | None = "NVDA", **tabs: list[dict]) -> Path:
    """build(path, Drivers=[{...}], Signals=[{...}], ...) -> path of the saved workbook.

    Tab keyword names use underscores for spaces: Base_case, Event_ladder, Source_log, Scoring_log.
    """
    wb = openpyxl.load_workbook(TEMPLATE)
    if ticker is not None:
        wb["README"]["B2"] = ticker
    for kw, rows in tabs.items():
        tab = kw.replace("_", " ")
        cols = COLUMNS[tab]
        ws = wb[tab]
        for i, row in enumerate(rows, start=2):
            for field, value in row.items():
                ws[f"{cols[field]}{i}"] = value
    wb.save(path)
    return path


def minimal(**overrides) -> dict:
    """A small valid sheet: one driver, one Tier A signal, one source, one base case."""
    sheet = {
        "Drivers": [{"code": "D1", "name": "Hyperscaler capex", "impact": "H"}],
        "Signals": [{"code": "S1", "driver": "D1", "name": "Hyperscaler capex, $B", "tier": "A",
                     "cadence": "Quarterly", "polarity": "Higher is better", "tolerance": 0.1,
                     "staleness": 120}],
        "Source_log": [{"code": "R1", "name": "AMZN 10-Q", "url": "https://www.sec.gov/", "tier": "A"}],
        "Base_case": [{"version": "v1", "case_type": "Consensus", "signal": "S1", "period": "Q3 FY26",
                       "value": 100, "source": "R1"}],
        "Scoring_log": [],
    }
    sheet.update(overrides)
    return sheet
