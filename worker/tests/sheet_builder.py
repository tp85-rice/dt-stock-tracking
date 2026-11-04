"""Build filled driver sheets for tests from the real template (thin wrapper over worker.sheet_writer)."""

from __future__ import annotations

from worker.sheet_writer import COLUMNS, TEMPLATE, build  # noqa: F401  (re-exported for tests)


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
