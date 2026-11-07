"""Golden test: the spreadsheet and the database must give the same colours.

1. Fill the real template with rows that hit every rule.
2. Let LibreOffice recalculate the template's own formulas.
3. Import the same file into the test database.
4. Compare colour, data status and variance row by row.

If this fails, one of the two is wrong: fix it before trusting either.
Needs LibreOffice (`soffice`) and a test database; skipped otherwise.
"""

from __future__ import annotations

import datetime as dt
import shutil
import subprocess

import openpyxl
import pytest

from worker.driver_sheet import parse
from worker.import_xlsx import import_sheet
from worker.tests.sheet_builder import build

SOFFICE = shutil.which("soffice") or shutil.which("libreoffice")
pytestmark = pytest.mark.skipif(not SOFFICE, reason="LibreOffice not installed")

TODAY = dt.date.today()


def ago(days: int) -> dt.date:
    return TODAY - dt.timedelta(days=days)


def sig(code, driver, polarity, tolerance=0.1, staleness=100, tier="A"):
    return {"code": code, "driver": driver, "name": f"signal {code}", "tier": tier,
            "polarity": polarity, "tolerance": tolerance, "staleness": staleness}


SIGNALS = [
    sig("S1", "D1", "Higher is better"),
    sig("S2", "D1", "Lower is better"),
    sig("S3", "D1", "Higher is better", tolerance=None, staleness=None),
    sig("S4", "D1", "Event ladder"),
    sig("S5", "D1", None),
    sig("S6", "D2", "Higher is better", tier="C"),
    *[sig(f"S{i}", "D4", "Higher is better") for i in range(7, 13)],
]
DRIVERS = [{"code": c, "name": f"driver {c}"} for c in ("D1", "D2", "D3", "D4")]


def base(signal, period, value, case="Consensus", version="v1"):
    return {"version": version, "case_type": case, "signal": signal, "period": period, "value": value}


BASE = [base(s, "Q1", 100) for s in ("S1", "S2", "S3", "S4", "S5", "S6")] + [
    base("S1", "Q2", 0),
    base("S1", "Q3", 100, case="Management"),
    base("S1", "Q4", -50),
    base("S2", "Q1", 80, version="v2"),
    base("S3", "Q1", 500, case="Thesis"),                      # Consensus exists for S3 Q1, so not used
    base("S1", "Q5", 100, case="Thesis"),                      # no Consensus: scored against Thesis
    base("S1", "Q6", 100, case="Management"),                  # Management alone: never scored
]


def obs(signal, value, period="Q1", version="v1", days=1):
    return {"date": ago(days), "signal": signal, "value": value, "version": version, "period": period}


SCORES = [
    obs("S1", 120), obs("S1", 100), obs("S1", 95), obs("S1", 90), obs("S1", 89.99), obs("S1", 50),
    obs("S2", 80), obs("S2", 100), obs("S2", 110), obs("S2", 110.01), obs("S2", 150),
    obs("S2", 75, version="v2"),                               # scored against v2 = 80
    obs("S3", 99.9), obs("S3", 100), obs("S3", 120, days=5000),  # blank tolerance, no staleness
    obs("S4", 100), obs("S5", 100),                            # event-ladder / no polarity -> GREY
    obs("S1", None),                                           # missing
    obs("S1", 120, days=101), obs("S1", 120, days=100),         # stale / just fresh
    obs("S1", 120, period="Q9"),                               # no base case
    obs("S1", 120, version="v7"),                              # no base case
    obs("S1", 5, period="Q2"),                                 # zero base
    obs("S1", 120, period="Q3"),                               # management only
    obs("S1", 95, period="Q5"), obs("S1", 80, period="Q5"),    # Thesis fallback: YELLOW, RED
    obs("S1", 120, period="Q6"),                               # Management only -> GREY
    obs("S1", -40, period="Q4"), obs("S1", -60, period="Q4"),  # negative base
    obs("S1", 120, period="q1", version="V1"),                 # case-insensitive match
    dict(obs("S1", None), withheld="Y"),                       # withheld -> RED
    dict(obs("S1", 120), withheld="Y"),                        # value wins over the flag
]


def step(signal, n, status, target_days, actual_days=None):
    target = ago(target_days) if target_days is not None else None
    actual = ago(actual_days) if actual_days is not None else None
    return {"signal": signal, "step": n, "milestone": f"step {n}", "status": status,
            "target": target, "actual": actual}


EVENTS = [
    step("S4", 1, "Failed", -30),
    step("S4", 2, "Slipped", -30),
    step("S4", 3, "Occurred", 10, 12),     # early
    step("S4", 4, "Occurred", 10, 10),     # on time
    step("S4", 5, "Occurred", 10, 5),      # 5 days late
    step("S4", 6, "Occurred", 10, None),   # no actual date
    step("S4", 7, "Pending", 1),           # target passed
    step("S4", 8, "Pending", 0),           # due today
    step("S4", 9, "Pending", None),
    step("S4", 10, None, -30),
]


def _recalculate(src, out_dir, tmp_path):
    profile = (tmp_path / "lo-profile").as_uri()
    subprocess.run(
        [SOFFICE, f"-env:UserInstallation={profile}", "--headless", "--calc",
         "--convert-to", "xlsx", "--outdir", str(out_dir), str(src)],
        check=True, capture_output=True, timeout=180)
    return openpyxl.load_workbook(out_dir / src.name, data_only=True)


def test_database_matches_spreadsheet(db, tmp_path):
    src = build(tmp_path / "golden.xlsx", ticker="GOLD", Drivers=DRIVERS, Signals=SIGNALS,
                Base_case=BASE, Scoring_log=SCORES, Event_ladder=EVENTS,
                Source_log=[{"code": "R1", "url": "https://example.com"}])
    excel = _recalculate(src, tmp_path / "out", tmp_path)

    sheet = parse(src)
    assert sheet.errors == [], sheet.errors
    db.execute("select set_config('app.today', %s, true)", (TODAY.isoformat(),))
    import_sheet(db, sheet, is_test=True)

    # Scoring log: G = variance, K = data status, L = colour.
    ws = excel["Scoring log"]
    rows = db.execute(
        "select data_status, colour, variance, base_type from v_scores where ticker = 'GOLD' order by observation_id"
    ).fetchall()
    assert len(rows) == len(SCORES)
    assert any(r[3] == "Thesis" for r in rows)
    for i, (status, colour, variance, base_type) in enumerate(rows, start=2):
        x_var = ws[f"G{i}"].value
        assert (ws[f"K{i}"].value, ws[f"L{i}"].value) == (status, colour), f"Scoring log row {i}"
        assert (ws[f"Q{i}"].value or None) == base_type, f"Scoring log row {i}, scored against"
        if isinstance(x_var, (int, float)):
            assert float(variance) == pytest.approx(x_var), f"Scoring log row {i} variance"
        else:
            assert variance is None, f"Scoring log row {i} variance"

    # Event ladder: G = days late, H = colour.
    ws = excel["Event ladder"]
    rows = db.execute(
        "select colour, days_late from v_event_ladder where ticker = 'GOLD' order by step_no").fetchall()
    for i, (colour, days_late) in enumerate(rows, start=2):
        x_late = ws[f"G{i}"].value
        assert ws[f"H{i}"].value == colour, f"Event ladder row {i}"
        assert (x_late if x_late not in ("", None) else None) == days_late, f"Event ladder row {i} days late"

    # Drivers: J = # signals, K = # tier A/B, L = status.
    ws = excel["Drivers"]
    rows = db.execute(
        "select n_signals, n_tier_ab, driver_status from v_driver_status where ticker = 'GOLD' order by code"
    ).fetchall()
    for i, row in enumerate(rows, start=2):
        assert (ws[f"J{i}"].value, ws[f"K{i}"].value, ws[f"L{i}"].value) == row, f"Drivers row {i}"
