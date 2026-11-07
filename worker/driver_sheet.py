"""Read and validate a filled copy of templates/stock_driver_template.xlsx.

Only the yellow input cells are read. The grey formula cells are ignored:
colours are recalculated by the database (supabase/migrations/*_scoring_views.sql).

This module never touches the database, so it can be tested and run on its own
(`python -m worker.import_xlsx inputs/NVDA_driver_sheet.xlsx --dry-run`).
"""

from __future__ import annotations

import datetime as dt
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import openpyxl
from openpyxl.utils import column_index_from_string

# Allowed values, copied from the template's dropdowns (templates/build_templates.py).
IMPACT = ["H", "M", "L"]
DIRECTION = ["Upside", "Downside", "Both"]
CONFIDENCE = ["High", "Medium", "Low"]
TIER = ["A", "B", "C"]
CADENCE = ["Daily", "Weekly", "Monthly", "Quarterly", "Event"]
POLARITY = ["Higher is better", "Lower is better", "Event ladder"]
CASE_TYPE = ["Consensus", "Management", "Thesis"]
EVENT_STATUS = ["Pending", "Occurred", "Slipped", "Failed"]
ACCESS = ["API", "Download", "Scrape", "Manual", "Vendor"]
COST = ["Free", "Paid", "Unknown"]
YES_NO = ["Yes", "No", "Unknown"]
ARROW = ["Accelerating", "Flat", "Decelerating", "n/a"]
DRIVER_TYPE = ["Core", "Option", "Mechanism", "Event"]
EVENT_KIND = ["Milestone", "Catalyst", "Falsification test", "Thesis breaker", "Disclosure"]
CASE_TYPE_SCORED = "Consensus"
SCORED_CASE_TYPES = ("Consensus", "Thesis")  # Thesis only when no Consensus row (decision 2026-11-07)

TICKER_RE = re.compile(r"^[A-Z0-9][A-Z0-9.\-]{0,11}$")
CODE_RE = re.compile(r"^[A-Z0-9_\-]+$")
MAX_SIGNALS_PER_DRIVER = 5


@dataclass
class Issue:
    level: str  # "error" blocks the import, "warning" does not
    tab: str
    row: int | None
    message: str

    def __str__(self) -> str:
        where = f"{self.tab} row {self.row}" if self.row else self.tab
        return f"[{self.level.upper()}] {where}: {self.message}"


@dataclass
class DriverSheet:
    path: Path
    ticker: str | None = None
    archetype: str | None = None
    owner_note: str | None = None
    drivers: list[dict] = field(default_factory=list)
    signals: list[dict] = field(default_factory=list)
    base_case: list[dict] = field(default_factory=list)
    event_ladder: list[dict] = field(default_factory=list)
    sources: list[dict] = field(default_factory=list)
    scores: list[dict] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.level == "error"]

    @property
    def warnings(self) -> list[Issue]:
        return [i for i in self.issues if i.level == "warning"]

    def summary(self) -> str:
        return (
            f"{self.ticker}: {len(self.drivers)} drivers, {len(self.signals)} signals, "
            f"{len(self.base_case)} base case rows, {len(self.event_ladder)} event steps, "
            f"{len(self.sources)} sources, {len(self.scores)} observations"
        )


class _Row:
    """One spreadsheet row, with converters that record problems instead of raising."""

    def __init__(self, sheet: DriverSheet, tab: str, row_no: int, cells: dict[str, Any]):
        self.sheet, self.tab, self.row_no, self.cells = sheet, tab, row_no, cells

    def _issue(self, level: str, msg: str) -> None:
        self.sheet.issues.append(Issue(level, self.tab, self.row_no, msg))

    def error(self, msg: str) -> None:
        self._issue("error", msg)

    def warn(self, msg: str) -> None:
        self._issue("warning", msg)

    def text(self, col: str, label: str, required: bool = False) -> str | None:
        value = _text(self.cells.get(col))
        if value is None and required:
            self.error(f"{label} (column {col}) is required")
        return value

    def code(self, col: str, label: str, required: bool = False) -> str | None:
        value = self.text(col, label, required)
        if value is None:
            return None
        value = re.sub(r"\s+", "", value).upper()
        if not CODE_RE.match(value):
            self.error(f"{label} '{value}' may only contain letters, digits, _ and -")
        return value

    def choice(self, col: str, label: str, options: list[str], required: bool = False) -> str | None:
        value = self.text(col, label, required)
        if value is None:
            return None
        for opt in options:
            if value.lower() == opt.lower():
                return opt
        self.error(f"{label} '{value}' is not one of: {', '.join(options)}")
        return None

    def yes(self, col: str, label: str) -> bool:
        """Y/N cell -> bool. Blank counts as N."""
        value = self.choice(col, label, ["Y", "N", "Yes", "No"])
        return value in ("Y", "Yes")

    def number(self, col: str, label: str, required: bool = False) -> float | None:
        raw = self.cells.get(col)
        if raw is None or (isinstance(raw, str) and not raw.strip()):
            if required:
                self.error(f"{label} (column {col}) is required")
            return None
        if isinstance(raw, bool):
            self.error(f"{label} must be a number, got {raw!r}")
            return None
        if isinstance(raw, (int, float)):
            return float(raw)
        if isinstance(raw, str):
            s = raw.strip().replace(",", "").replace("$", "")
            pct = s.endswith("%")
            try:
                n = float(s.rstrip("%"))
                return n / 100 if pct else n
            except ValueError:
                pass
        self.error(f"{label} must be a number, got {raw!r}")
        return None

    def integer(self, col: str, label: str, lo: int | None = None, hi: int | None = None,
                required: bool = False) -> int | None:
        n = self.number(col, label, required)
        if n is None:
            return None
        if n != int(n):
            self.error(f"{label} must be a whole number, got {n}")
            return None
        n = int(n)
        if (lo is not None and n < lo) or (hi is not None and n > hi):
            self.error(f"{label} must be between {lo} and {hi}, got {n}")
            return None
        return n

    def date(self, col: str, label: str, required: bool = False) -> dt.date | None:
        raw = self.cells.get(col)
        if raw is None or (isinstance(raw, str) and not raw.strip()):
            if required:
                self.error(f"{label} (column {col}) is required")
            return None
        if isinstance(raw, dt.datetime):
            return raw.date()
        if isinstance(raw, dt.date):
            return raw
        if isinstance(raw, str):
            try:
                return dt.date.fromisoformat(raw.strip()[:10])
            except ValueError:
                pass
        self.error(f"{label} must be a date (YYYY-MM-DD), got {raw!r}")
        return None


def _text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    if isinstance(value, (dt.datetime, dt.date)):
        value = value.isoformat()[:10]
    s = str(value).strip()
    return s or None


def _label(value: Any) -> str | None:
    """Version and period labels: trimmed, inner whitespace collapsed."""
    s = _text(value)
    return re.sub(r"\s+", " ", s) if s else None


def _rows(ws, sheet: DriverSheet, cols: str):
    """Yield non-empty rows (from row 2) as _Row objects keyed by column letter."""
    index = {col: column_index_from_string(col) - 1 for col in cols}
    rows = ws.iter_rows(min_row=2, max_col=max(index.values()) + 1, values_only=True)
    for row_no, values in enumerate(rows, start=2):
        cells = {col: values[i] if i < len(values) else None for col, i in index.items()}
        if all(_text(v) is None for v in cells.values()):
            continue
        yield _Row(sheet, ws.title, row_no, cells)


REQUIRED_TABS = ["README", "Drivers", "Signals", "Base case", "Event ladder", "Source log", "Scoring log"]


def parse(path: str | Path, ticker_override: str | None = None, allow_rename: bool = False) -> DriverSheet:
    """allow_rename: let ticker_override replace a different README ticker (used for --test trial imports)."""
    path = Path(path)
    sheet = DriverSheet(path=path)
    try:
        wb = openpyxl.load_workbook(path, data_only=False)
    except Exception as exc:  # noqa: BLE001 - surface any openpyxl failure as a sheet error
        sheet.issues.append(Issue("error", "file", None, f"cannot open workbook: {exc}"))
        return sheet

    missing = [t for t in REQUIRED_TABS if t not in wb.sheetnames]
    if missing:
        sheet.issues.append(Issue("error", "file", None,
                                  f"missing tabs {missing}; is this a copy of stock_driver_template.xlsx?"))
        return sheet

    _parse_readme(wb["README"], sheet, ticker_override, allow_rename)
    _parse_sources(wb["Source log"], sheet)
    _parse_drivers(wb["Drivers"], sheet)
    _parse_signals(wb["Signals"], sheet)
    _parse_base_case(wb["Base case"], sheet)
    _parse_event_ladder(wb["Event ladder"], sheet)
    _parse_scores(wb["Scoring log"], sheet)
    _cross_checks(sheet)
    return sheet


def _parse_readme(ws, sheet: DriverSheet, override: str | None, allow_rename: bool = False) -> None:
    ticker = _text(ws["B2"].value)
    ticker = ticker.upper() if ticker else None
    if override:
        override = override.upper()
        if ticker and ticker != override and not allow_rename:
            sheet.issues.append(Issue("error", "README", 2,
                                      f"ticker in sheet is {ticker} but --ticker {override} was given"))
        ticker = override
    if not ticker:
        sheet.issues.append(Issue("error", "README", 2, "Ticker (cell B2) is empty"))
    elif not TICKER_RE.match(ticker):
        sheet.issues.append(Issue("error", "README", 2, f"'{ticker}' is not a valid ticker symbol"))
    sheet.ticker = ticker
    sheet.archetype = _text(ws["B3"].value)
    sheet.owner_note = _text(ws["B4"].value)


def _dupes(sheet: DriverSheet, tab: str, keyed: list[tuple[Any, int]], what: str) -> None:
    counts = Counter(k for k, _ in keyed if k is not None)
    for key, row in keyed:
        if key is not None and counts[key] > 1:
            sheet.issues.append(Issue("error", tab, row, f"duplicate {what} {key}"))


def _parse_sources(ws, sheet: DriverSheet) -> None:
    keyed = []
    for r in _rows(ws, sheet, "ABCDEFGHIJK"):
        rec = {
            "code": r.code("A", "Source ID", required=True),
            "accessed_on": r.date("B", "Date accessed"),
            "name": r.text("C", "Source name"),
            "url": r.text("D", "URL"),
            "tier": r.choice("E", "Tier", TIER),
            "access_method": r.choice("F", "Access method", ACCESS),
            "cost": r.choice("G", "Cost", COST),
            "tos_note": r.text("H", "ToS / licensing note"),
            "redistribute": r.choice("I", "Redistribute on site?", YES_NO),
            "used_for": r.text("J", "Used for"),
            "reliability_note": r.text("K", "Reliability note"),
        }
        if not rec["url"]:
            r.warn("no URL: every number shown in the app should link to its source")
        sheet.sources.append(rec | {"_row": r.row_no})
        keyed.append((rec["code"], r.row_no))
    _dupes(sheet, "Source log", keyed, "Source ID")


def _parse_drivers(ws, sheet: DriverSheet) -> None:
    keyed = []
    for r in _rows(ws, sheet, "ABCDEFGHI"):  # J-L are formulas; M-P read below
        extra = _Row(sheet, ws.title, r.row_no,
                     {c: ws[f"{c}{r.row_no}"].value for c in "NOP"})
        rec = {
            "code": r.code("A", "Driver ID", required=True),
            "name": r.text("B", "Driver", required=True),
            "thesis": r.text("C", "Thesis"),
            "valuation_mechanism": r.text("D", "Valuation mechanism"),
            "horizon_years": r.integer("E", "Horizon (years)", 1, 5),
            "impact": r.choice("F", "Impact", IMPACT),
            "direction": r.choice("G", "Direction", DIRECTION),
            "evidence": r.text("H", "Evidence / citation"),
            "confidence": r.choice("I", "Confidence", CONFIDENCE),
            "notes": _text(ws.cell(row=r.row_no, column=13).value),
            "driver_type": extra.choice("N", "Driver type", DRIVER_TYPE),
            "share_of_price": extra.number("O", "Share of price"),
            "depends_on": None,
        }
        deps = extra.text("P", "Depends on")
        if deps:
            rec["depends_on"] = ", ".join(re.sub(r"\s+", "", d).upper() for d in re.split(r"[,;]", deps) if d.strip())
        if rec["share_of_price"] is not None and not 0 <= rec["share_of_price"] <= 1:
            r.error(f"Share of price must be between 0 and 1 (e.g. 0.30 = 30%), got {rec['share_of_price']}")
        sheet.drivers.append(rec | {"_row": r.row_no})
        keyed.append((rec["code"], r.row_no))
    _dupes(sheet, "Drivers", keyed, "Driver ID")


def _parse_signals(ws, sheet: DriverSheet) -> None:
    keyed = []
    for r in _rows(ws, sheet, "ABCDEFGHIJKLMNOP"):
        rec = {
            "code": r.code("A", "Signal ID", required=True),
            "driver_code": r.code("B", "Driver ID", required=True),
            "name": r.text("C", "Signal", required=True),
            "source_text": r.text("D", "Source"),
            "tier": r.choice("E", "Tier", TIER),
            "cadence": r.choice("F", "Cadence", CADENCE),
            "unit": r.text("G", "Unit"),
            "polarity": r.choice("H", "Polarity", POLARITY),
            "tolerance": r.number("I", "Tolerance band"),
            "max_staleness_days": r.integer("J", "Max staleness (days)", 0, 100000),
            "reliability": r.integer("K", "Reliability", 1, 5),
            "definition_change": r.text("L", "Definition change"),
            "notes": r.text("M", "Notes"),
            "binding_constraint": r.yes("N", "Binding constraint"),
            "kill_switch": r.yes("O", "Kill switch"),
            "threshold_anchor": r.text("P", "Threshold anchor"),
        }
        if rec["tolerance"] is not None:
            if rec["tolerance"] < 0:
                r.error("Tolerance band cannot be negative")
            elif rec["tolerance"] > 1:
                r.warn(f"Tolerance band {rec['tolerance']} means {rec['tolerance']:.0%}; "
                       "did you mean a fraction like 0.10 (= 10%)?")
        if rec["polarity"] is None and rec["code"]:
            r.warn("no polarity: this signal will always show GREY")
        if rec["tier"] is None and rec["code"]:
            r.warn("no tier: it will not count towards the 'at least one Tier A/B' rule")
        sheet.signals.append(rec | {"_row": r.row_no})
        keyed.append((rec["code"], r.row_no))
    _dupes(sheet, "Signals", keyed, "Signal ID")


def _parse_base_case(ws, sheet: DriverSheet) -> None:
    keyed = []
    for r in _rows(ws, sheet, "ABCDEFGHI"):
        rec = {
            "version": _label(r.cells["A"]),
            "snapshot_date": r.date("B", "Snapshot date"),
            "case_type": r.choice("C", "Case type", CASE_TYPE, required=True),
            "signal_code": r.code("D", "Signal ID", required=True),
            "period": _label(r.cells["E"]),
            "value": r.number("F", "Value", required=True),
            "unit": r.text("G", "Unit"),
            "source_code": r.code("H", "Source ID"),
            "notes": r.text("I", "Basis / notes"),
        }
        if not rec["version"]:
            r.error("Version (column A) is required, e.g. v1")
        if not rec["period"]:
            r.error("Period (column E) is required, e.g. Q4 FY26")
        if not rec["snapshot_date"]:
            r.warn("no snapshot date: you won't be able to tell when this base case was set")
        sheet.base_case.append(rec | {"_row": r.row_no})
        key = None
        if all(rec[k] for k in ("version", "case_type", "signal_code", "period")):
            key = (rec["version"].lower(), rec["case_type"], rec["signal_code"], rec["period"].lower())
        keyed.append((key, r.row_no))
    counts = Counter(k for k, _ in keyed if k)
    for key, row in keyed:
        if key and counts[key] > 1:
            sheet.issues.append(Issue(
                "error", "Base case", row,
                f"duplicate base case for signal {key[2]}, version {key[0]}, {key[1]}, period {key[3]}"
                " (Excel would add them together)"))


def _parse_event_ladder(ws, sheet: DriverSheet) -> None:
    keyed = []
    for r in _rows(ws, sheet, "ABCDEF"):  # G-H are formulas
        rec = {
            "signal_code": r.code("A", "Signal ID", required=True),
            "step_no": r.integer("B", "Step #", 0, 10000, required=True),
            "milestone": r.text("C", "Milestone", required=True),
            "target_date": r.date("D", "Base case target date"),
            "status": r.choice("E", "Status", EVENT_STATUS),
            "actual_date": r.date("F", "Actual date"),
            "source_code": _text(ws.cell(row=r.row_no, column=9).value),
            "notes": _text(ws.cell(row=r.row_no, column=10).value),
            "kind": None,
        }
        rec["kind"] = _Row(sheet, ws.title, r.row_no, {"K": ws.cell(row=r.row_no, column=11).value}
                           ).choice("K", "Kind", EVENT_KIND)
        if rec["source_code"]:
            rec["source_code"] = re.sub(r"\s+", "", rec["source_code"]).upper()
        if rec["status"] == "Occurred" and not rec["actual_date"]:
            r.warn("status is Occurred but there is no actual date")
        sheet.event_ladder.append(rec | {"_row": r.row_no})
        keyed.append(((rec["signal_code"], rec["step_no"]) if rec["signal_code"] else None, r.row_no))
    _dupes(sheet, "Event ladder", keyed, "(Signal ID, Step #)")


def _parse_scores(ws, sheet: DriverSheet) -> None:
    for r in _rows(ws, sheet, "ABCDE"):  # F-L are formulas; M-O read below
        rec = {
            "observed_on": r.date("A", "Date observed"),
            "signal_code": r.code("B", "Signal ID", required=True),
            "value": r.number("C", "Observed value"),
            "base_case_version": _label(r.cells["D"]),
            "period": _label(r.cells["E"]),
            "arrow": None,
            "source_code": None,
            "notes": _text(ws.cell(row=r.row_no, column=15).value),
        }
        more = _Row(sheet, ws.title, r.row_no, {"M": ws.cell(row=r.row_no, column=13).value,
                                                  "N": ws.cell(row=r.row_no, column=14).value,
                                                  "P": ws.cell(row=r.row_no, column=16).value})
        rec["arrow"] = more.choice("M", "Arrow", ARROW)
        rec["source_code"] = more.code("N", "Source ID")
        rec["withheld"] = more.yes("P", "Withheld?")
        if rec["withheld"] and rec["value"] is not None:
            r.warn("marked Withheld but has a value: the value wins and Withheld is ignored")
        if rec["value"] is None and not rec["withheld"]:
            r.warn("no observed value: this row will show GREY (Missing)")
        if not rec["observed_on"]:
            r.warn("no date observed: staleness cannot be checked")
        if not rec["base_case_version"] or not rec["period"]:
            r.warn("no base case version or period: this row will show GREY (No base case)")
        sheet.scores.append(rec | {"_row": r.row_no})


def _cross_checks(sheet: DriverSheet) -> None:
    drivers = {d["code"] for d in sheet.drivers if d["code"]}
    signals = {s["code"]: s for s in sheet.signals if s["code"]}
    sources = {s["code"] for s in sheet.sources if s["code"]}

    def need(tab: str, row: int, kind: str, code: str | None, known) -> None:
        if code and code not in known:
            sheet.issues.append(Issue("error", tab, row, f"{kind} {code} is not defined"))

    for s in sheet.signals:
        need("Signals", s["_row"], "Driver ID", s["driver_code"], drivers)
    for b in sheet.base_case:
        need("Base case", b["_row"], "Signal ID", b["signal_code"], signals)
        need("Base case", b["_row"], "Source ID", b["source_code"], sources)
    for e in sheet.event_ladder:
        need("Event ladder", e["_row"], "Signal ID", e["signal_code"], signals)
        need("Event ladder", e["_row"], "Source ID", e["source_code"], sources)
        sig = signals.get(e["signal_code"])
        # Disclosure steps, falsification tests, thesis breakers and catalysts may sit on numeric
        # signals; only plain milestone steps belong to an "Event ladder" signal.
        if (sig and sig["polarity"] and sig["polarity"] != "Event ladder"
                and e.get("kind") in (None, "Milestone")):
            sheet.issues.append(Issue("warning", "Event ladder", e["_row"],
                                      f"signal {e['signal_code']} has polarity '{sig['polarity']}', "
                                      "not 'Event ladder'"))
    for o in sheet.scores:
        need("Scoring log", o["_row"], "Signal ID", o["signal_code"], signals)
        need("Scoring log", o["_row"], "Source ID", o["source_code"], sources)

    # Scoring log rows with neither a Consensus nor a Thesis base case (Thesis is used when Consensus is missing).
    consensus = {(b["signal_code"], (b["version"] or "").lower(), (b["period"] or "").lower())
                 for b in sheet.base_case if b["case_type"] in SCORED_CASE_TYPES}
    for o in sheet.scores:
        if o["signal_code"] in signals and o["base_case_version"] and o["period"]:
            key = (o["signal_code"], o["base_case_version"].lower(), o["period"].lower())
            if key not in consensus:
                sheet.issues.append(Issue(
                    "warning", "Scoring log", o["_row"],
                    f"no Consensus or Thesis base case for {o['signal_code']} {o['base_case_version']} "
                    f"{o['period']}: this row will show GREY (No base case)"))

    # Driver-level rules (same as the Drivers tab's status column).
    for d in sheet.drivers:
        mine = [s for s in sheet.signals if s["driver_code"] == d["code"]]
        if not mine:
            sheet.issues.append(Issue("warning", "Drivers", d["_row"], f"driver {d['code']} has no signals"))
        elif not any(s["tier"] in ("A", "B") for s in mine):
            sheet.issues.append(Issue("warning", "Drivers", d["_row"],
                                      f"driver {d['code']} has no Tier A or B signal: it will show as "
                                      "narrative-only"))
        stars = [s["code"] for s in mine if s.get("binding_constraint")]
        if len(stars) > 1:
            sheet.issues.append(Issue("warning", "Drivers", d["_row"],
                                      f"driver {d['code']} has {len(stars)} binding-constraint signals "
                                      f"({', '.join(stars)}); pick the one that gates it"))
        for dep in (d.get("depends_on") or "").split(", "):
            if dep and dep not in drivers:
                sheet.issues.append(Issue("error", "Drivers", d["_row"], f"Depends on {dep}: not a Driver ID"))
        if len(mine) > MAX_SIGNALS_PER_DRIVER:
            sheet.issues.append(Issue("warning", "Drivers", d["_row"],
                                      f"driver {d['code']} has {len(mine)} signals (cap is "
                                      f"{MAX_SIGNALS_PER_DRIVER})"))
