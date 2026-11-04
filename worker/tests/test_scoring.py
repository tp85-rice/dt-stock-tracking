"""Colour rules in the database views (v_scores, v_event_ladder, v_driver_status).

"Today" is pinned to 2026-11-03 by the db fixture.
"""

from __future__ import annotations

import pytest


def _setup(db, polarity="Higher is better", tolerance=0.10, staleness=120, base=100.0,
           version="v1", period="Q3 FY26", case_type="Consensus", tier="A"):
    db.execute("insert into tickers (symbol) values ('NVDA')")
    db.execute("insert into drivers (ticker, code, name) values ('NVDA', 'D1', 'Capex')")
    db.execute(
        """insert into signals (ticker, code, driver_code, name, tier, polarity, tolerance,
                                max_staleness_days)
           values ('NVDA', 'S1', 'D1', 'Capex $B', %s, %s, %s, %s)""",
        (tier, polarity, tolerance, staleness))
    if base is not None:
        db.execute(
            """insert into base_case (ticker, version, case_type, signal_code, period, value)
               values ('NVDA', %s, %s, 'S1', %s, %s)""", (version, case_type, period, base))


def _score(db, value, observed_on="2026-11-01", version="v1", period="Q3 FY26"):
    db.execute(
        """insert into observations (ticker, signal_code, observed_on, value, base_case_version, period)
           values ('NVDA', 'S1', %s, %s, %s, %s)""", (observed_on, value, version, period))
    return db.execute(
        "select colour, data_status, variance from v_scores order by observation_id desc limit 1"
    ).fetchone()


# (polarity, tolerance, observed, expected colour) with a base case of 100
CASES = [
    ("Higher is better", 0.10, 110, "GREEN"),
    ("Higher is better", 0.10, 100, "GREEN"),     # exactly on base
    ("Higher is better", 0.10, 95, "YELLOW"),     # 5% miss
    ("Higher is better", 0.10, 90, "YELLOW"),     # exactly on the tolerance boundary
    ("Higher is better", 0.10, 89.99, "RED"),
    ("Higher is better", 0.10, 80, "RED"),        # 20% miss
    ("Lower is better", 0.10, 90, "GREEN"),
    ("Lower is better", 0.10, 100, "GREEN"),
    ("Lower is better", 0.10, 110, "YELLOW"),     # boundary
    ("Lower is better", 0.10, 110.01, "RED"),
    ("Higher is better", None, 99.9, "RED"),      # blank tolerance counts as 0
    ("Higher is better", None, 100, "GREEN"),
    ("Event ladder", 0.10, 100, "GREY"),          # numeric scoring does not apply
    (None, 0.10, 100, "GREY"),                    # no polarity set
]


@pytest.mark.parametrize("polarity,tolerance,observed,expected", CASES)
def test_colour_bands(db, polarity, tolerance, observed, expected):
    _setup(db, polarity=polarity, tolerance=tolerance)
    colour, status, _ = _score(db, observed)
    assert (colour, status) == (expected, "OK")


def test_variance_uses_absolute_base(db):
    _setup(db, base=-50)
    colour, _, variance = _score(db, -40)  # less negative = better: +20%
    assert float(variance) == pytest.approx(0.2)
    assert colour == "GREEN"


def test_missing_value_is_grey(db):
    _setup(db)
    assert _score(db, None)[:2] == ("GREY", "Missing")


def test_stale_is_grey(db):
    _setup(db, staleness=120)
    assert _score(db, 120, observed_on="2026-07-05")[:2] == ("GREY", "Stale")   # 121 days old
    assert _score(db, 120, observed_on="2026-07-06")[:2] == ("GREEN", "OK")     # exactly 120 days


def test_no_staleness_limit_never_stale(db):
    _setup(db, staleness=None)
    assert _score(db, 120, observed_on="2020-01-01")[:2] == ("GREEN", "OK")


def test_no_base_case_is_grey(db):
    _setup(db, base=None)
    assert _score(db, 120)[:2] == ("GREY", "No base case")


def test_wrong_version_or_period_is_grey(db):
    _setup(db)
    assert _score(db, 120, version="v2")[:2] == ("GREY", "No base case")
    assert _score(db, 120, period="Q4 FY26")[:2] == ("GREY", "No base case")


def test_matching_is_case_insensitive(db):
    _setup(db, version="v1", period="Q3 FY26")
    assert _score(db, 120, version="V1", period="q3 fy26")[:2] == ("GREEN", "OK")


def test_management_rows_are_not_scored(db):
    _setup(db, case_type="Management")
    assert _score(db, 120)[:2] == ("GREY", "No base case")


def test_zero_base_case_is_grey_but_ok(db):
    # Same as the spreadsheet: variance blank, Data status OK, colour GREY.
    _setup(db, base=0)
    colour, status, variance = _score(db, 5)
    assert (colour, status, variance) == ("GREY", "OK", None)


def test_changing_tolerance_recolours_history(db):
    _setup(db, tolerance=0.10)
    assert _score(db, 85)[0] == "RED"
    db.execute("update signals set tolerance = 0.20 where code = 'S1'")
    assert db.execute("select colour from v_scores").fetchone()[0] == "YELLOW"


def test_latest_signal_view(db):
    _setup(db)
    assert db.execute("select colour, data_status from v_signal_latest").fetchone() == ("GREY", "No data")
    _score(db, 80, observed_on="2026-08-01")
    _score(db, 120, observed_on="2026-10-01")
    row = db.execute("select colour, age_days from v_signal_latest").fetchone()
    assert row == ("GREEN", 33)


# ---------------------------------------------------------------- event ladder

@pytest.mark.parametrize("status,target,actual,expected,days_late", [
    ("Failed", "2026-12-01", None, "RED", None),
    ("Slipped", "2026-12-01", None, "RED", None),
    ("Occurred", "2026-10-01", "2026-09-28", "GREEN", -3),
    ("Occurred", "2026-10-01", "2026-10-01", "GREEN", 0),
    ("Occurred", "2026-10-01", "2026-10-05", "YELLOW", 4),
    ("Occurred", "2026-10-01", None, "GREEN", None),     # no actual date: treated as on time
    ("Pending", "2026-11-02", None, "YELLOW", None),     # target passed
    ("Pending", "2026-11-03", None, "PENDING", None),    # due today, not yet late
    ("Pending", None, None, "PENDING", None),
    (None, "2026-12-01", None, "PENDING", None),
])
def test_event_ladder(db, status, target, actual, expected, days_late):
    _setup(db, polarity="Event ladder", base=None)
    db.execute(
        """insert into event_ladder (ticker, signal_code, step_no, milestone, target_date, status,
                                     actual_date)
           values ('NVDA', 'S1', 1, 'Pad arrival', %s, %s, %s)""", (target, status, actual))
    assert db.execute("select colour, days_late from v_event_ladder").fetchone() == (expected, days_late)


# ---------------------------------------------------------------- driver status

def test_driver_status(db):
    _setup(db, tier="C")
    assert db.execute("select driver_status from v_driver_status").fetchone()[0] == "narrative-only"
    db.execute("update signals set tier = 'B'")
    assert db.execute("select driver_status from v_driver_status").fetchone()[0] == "OK"
    for i in range(2, 7):
        db.execute("insert into signals (ticker, code, driver_code, name, tier) "
                   "values ('NVDA', %s, 'D1', 'x', 'A')", (f"S{i}",))
    assert db.execute("select n_signals, driver_status from v_driver_status").fetchone() == (6, "over cap (5)")
    db.execute("insert into drivers (ticker, code, name) values ('NVDA', 'D2', 'Empty')")
    assert db.execute("select driver_status from v_driver_status where code = 'D2'").fetchone()[0] == "no signals"


# ---------------------------------------------------------------- base case is append-only

def test_base_case_cannot_be_changed(db):
    _setup(db)
    with pytest.raises(Exception, match="cannot be changed"):
        with db.transaction():
            db.execute("update base_case set value = 1")
    with pytest.raises(Exception, match="cannot be deleted"):
        with db.transaction():
            db.execute("delete from base_case")


def test_test_ticker_can_be_deleted_whole(db):
    db.execute("insert into tickers (symbol, is_test) values ('TEST', true)")
    db.execute("insert into drivers (ticker, code, name) values ('TEST', 'D1', 'x')")
    db.execute("insert into signals (ticker, code, driver_code, name) values ('TEST', 'S1', 'D1', 'x')")
    db.execute("insert into base_case (ticker, version, case_type, signal_code, period, value) "
               "values ('TEST', 'v1', 'Consensus', 'S1', 'Q1', 1)")
    db.execute("insert into observations (ticker, signal_code, value) values ('TEST', 'S1', 1)")
    db.execute("select app.delete_test_ticker('TEST')")
    assert db.execute("select count(*) from signals where ticker = 'TEST'").fetchone()[0] == 0


def test_real_ticker_cannot_use_delete_test_ticker(db):
    _setup(db)
    with pytest.raises(Exception, match="not a test ticker"):
        with db.transaction():
            db.execute("select app.delete_test_ticker('NVDA')")


def test_changes_are_audited(db):
    _setup(db)
    db.execute("update signals set tolerance = 0.2")
    row = db.execute(
        "select action, before->>'tolerance', after->>'tolerance' from audit_log "
        "where table_name = 'signals' order by id desc limit 1").fetchone()
    assert row == ("update", "0.1", "0.2")


# ---------------------------------------------------------------- template v2 (thesis fields)

def test_withheld_metric_is_red(db):
    # House Rule: a metric withheld on a natural disclosure occasion is a signal.
    _setup(db)
    db.execute(
        """insert into observations (ticker, signal_code, observed_on, value, base_case_version, period, withheld)
           values ('NVDA', 'S1', '2026-11-01', null, 'v1', 'Q3 FY26', true)""")
    assert db.execute("select colour, data_status from v_scores").fetchone() == ("RED", "Withheld")
    assert db.execute("select colour from v_signal_latest").fetchone()[0] == "RED"


def test_withheld_flag_ignored_when_value_present(db):
    _setup(db)
    db.execute(
        """insert into observations (ticker, signal_code, observed_on, value, base_case_version, period, withheld)
           values ('NVDA', 'S1', '2026-11-01', 120, 'v1', 'Q3 FY26', true)""")
    assert db.execute("select colour, data_status from v_scores").fetchone() == ("GREEN", "OK")


def test_thesis_rows_are_not_scored(db):
    _setup(db, case_type="Thesis")
    assert _score(db, 120)[:2] == ("GREY", "No base case")
