"""Importing a sheet into the database."""

from __future__ import annotations

import datetime as dt

import pytest

from worker.driver_sheet import parse
from worker.import_xlsx import SheetImportError, import_sheet, main
from worker.tests.sheet_builder import build, minimal

OBS = [{"date": dt.date(2026, 11, 1), "signal": "S1", "value": 95, "version": "v1", "period": "Q3 FY26",
        "arrow": "Flat", "source": "R1"}]


def _import(db, tmp_path, name="x.xlsx", is_test=False, ticker="NVDA", **tabs):
    sheet = parse(build(tmp_path / name, ticker=ticker, **minimal(**tabs)))
    assert sheet.errors == [], sheet.errors
    return import_sheet(db, sheet, is_test=is_test)


def test_import_and_score(db, tmp_path):
    _import(db, tmp_path, Scoring_log=OBS)
    assert db.execute("select colour, data_status from v_scores").fetchone() == ("YELLOW", "OK")
    assert db.execute("select count(*) from audit_log where actor_label like 'import_xlsx:%'").fetchone()[0] > 0


def test_reimport_is_idempotent(db, tmp_path):
    _import(db, tmp_path, Scoring_log=OBS)
    _import(db, tmp_path, Scoring_log=OBS)
    counts = db.execute(
        "select (select count(*) from drivers), (select count(*) from signals), "
        "(select count(*) from base_case), (select count(*) from observations)").fetchone()
    assert counts == (1, 1, 1, 1)


def test_reimport_updates_signal_rules(db, tmp_path):
    _import(db, tmp_path, Scoring_log=OBS)
    _import(db, tmp_path, Scoring_log=OBS, Signals=[
        {"code": "S1", "driver": "D1", "name": "Capex", "tier": "A", "polarity": "Higher is better",
         "tolerance": 0.01}])
    assert db.execute("select colour from v_scores").fetchone()[0] == "RED"


def test_changed_base_case_is_refused(db, tmp_path):
    _import(db, tmp_path)
    changed = [{"version": "v1", "case_type": "Consensus", "signal": "S1", "period": "Q3 FY26", "value": 120}]
    with pytest.raises(SheetImportError, match="add it as a new version"):
        _import(db, tmp_path, Base_case=changed)


def test_new_base_case_version_is_added(db, tmp_path):
    _import(db, tmp_path)
    both = [{"version": "v1", "case_type": "Consensus", "signal": "S1", "period": "Q3 FY26", "value": 100},
            {"version": "v2", "case_type": "Consensus", "signal": "S1", "period": "Q3 FY26", "value": 120}]
    _import(db, tmp_path, Base_case=both)
    assert db.execute("select count(*) from base_case").fetchone()[0] == 2


def test_app_observations_survive_reimport(db, tmp_path):
    _import(db, tmp_path, Scoring_log=OBS)
    db.execute("insert into observations (ticker, signal_code, value, origin) values ('NVDA', 'S1', 1, 'proposal')")
    _import(db, tmp_path, Scoring_log=[])
    assert db.execute("select origin from observations").fetchall() == [("proposal",)]


def test_removed_rows_are_reported_not_deleted(db, tmp_path):
    _import(db, tmp_path, Drivers=[{"code": "D1", "name": "a"}, {"code": "D2", "name": "b"}])
    notes = _import(db, tmp_path)
    assert any("drivers): D2" in n for n in notes)
    assert db.execute("select count(*) from drivers").fetchone()[0] == 2


def test_test_flag_must_match_existing_ticker(db, tmp_path):
    _import(db, tmp_path, ticker="TEST", is_test=True)
    with pytest.raises(SheetImportError, match="already exists as a test ticker"):
        _import(db, tmp_path, ticker="TEST", is_test=False)


def test_failed_import_writes_nothing(db, tmp_path):
    _import(db, tmp_path)
    changed = [{"version": "v1", "case_type": "Consensus", "signal": "S1", "period": "Q3 FY26", "value": 1}]
    with pytest.raises(SheetImportError):
        _import(db, tmp_path, Drivers=[{"code": "D1", "name": "renamed"}], Base_case=changed)
    assert db.execute("select name from drivers").fetchone()[0] == "Hyperscaler capex"


def test_cli_dry_run(tmp_path, capsys):
    path = build(tmp_path / "x.xlsx", **minimal())
    assert main([str(path), "--dry-run"]) == 0
    assert "Dry run: the sheet is valid" in capsys.readouterr().out
    bad = build(tmp_path / "bad.xlsx", ticker=None)
    assert main([str(bad), "--dry-run"]) == 1


def test_import_template_v2_fields(db, tmp_path):
    _import(db, tmp_path,
            Drivers=[{"code": "D1", "name": "a", "type": "Core", "share": 0.4}],
            Signals=[{"code": "S1", "driver": "D1", "name": "x", "tier": "A", "polarity": "Higher is better",
                      "tolerance": 0.1, "star": "Y", "kill_switch": "Y", "anchor": "guide"}],
            Base_case=[{"version": "v1", "case_type": "Consensus", "signal": "S1", "period": "Q3 FY26", "value": 100},
                       {"version": "v1", "case_type": "Thesis", "signal": "S1", "period": "Q3 FY26", "value": 110}],
            Scoring_log=[{"date": dt.date(2026, 11, 1), "signal": "S1", "version": "v1", "period": "Q3 FY26",
                          "withheld": "Y"}])
    assert db.execute("select driver_type, share_of_price::float from drivers").fetchone() == ("Core", 0.4)
    assert db.execute("select binding_constraint, kill_switch, threshold_anchor from signals").fetchone() == (
        True, True, "guide")
    assert db.execute("select colour, data_status from v_scores").fetchone() == ("RED", "Withheld")


def test_cli_trial_import_under_test_ticker(tmp_path, capsys):
    path = build(tmp_path / "x.xlsx", ticker="NVDA", **minimal())
    assert main([str(path), "--ticker", "TEST", "--dry-run"]) == 1          # real rename: refused
    assert main([str(path), "--ticker", "TEST", "--test", "--dry-run"]) == 0  # trial import: allowed
