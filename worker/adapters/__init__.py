"""Data feeds ("adapters"). Every adapter has the same shape:

    adapter(ticker, signal_code, params) -> list[Reading]

It only *reads* sources and returns proposed readings. It never writes to the database: worker.run_feeds turns
readings into proposals for the review queue. Add a source by writing one module and registering it in ADAPTERS.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class Reading:
    period: str                    # must match the Base case labels, e.g. "Q3 FY27", "Q3 CY26", "Sep 2026"
    value: float | None
    observed_on: dt.date           # when the number became public (filing date)
    source_url: str
    quote: str                     # what was read, for the reviewer (fact name and raw value, or a sentence)
    title: str
    notes: str = ""
    check: dict = field(default_factory=dict)   # machine-readable evidence (facts used, arithmetic)


Adapter = Callable[[str, str, dict], list[Reading]]


def registry() -> dict[str, Adapter]:
    from worker.adapters import edgar, tsmc

    return {
        "edgar_xbrl": edgar.xbrl_signal,
        "edgar_capex_sum": edgar.capex_sum,
        "tsmc_monthly_yoy": tsmc.monthly_yoy,
    }
