"""Reading and validating a filled template (no database needed)."""

from __future__ import annotations

import datetime as dt

from worker.driver_sheet import parse
from worker.tests.sheet_builder import build, minimal


def _msgs(sheet, level="error"):
    return [str(i) for i in sheet.issues if i.level == level]


def test_blank_template_needs_a_ticker(tmp_path):
    sheet = parse(build(tmp_path / "x.xlsx", ticker=None))
    assert any("Ticker (cell B2) is empty" in m for m in _msgs(sheet))


def test_minimal_sheet_is_valid(tmp_path):
    sheet = parse(build(tmp_path / "x.xlsx", **minimal()))
    assert sheet.errors == []
    assert sheet.ticker == "NVDA"
    assert [d["code"] for d in sheet.drivers] == ["D1"]
    assert sheet.signals[0]["tolerance"] == 0.1


def test_ticker_override_must_match(tmp_path):
    path = build(tmp_path / "x.xlsx", ticker="NVDA", **minimal())
    assert any("--ticker AMZN" in m for m in _msgs(parse(path, ticker_override="AMZN")))
    path = build(tmp_path / "y.xlsx", ticker=None, **minimal())
    assert parse(path, ticker_override="test").ticker == "TEST"


def test_codes_are_normalised(tmp_path):
    sheet = parse(build(tmp_path / "x.xlsx", **minimal(
        Drivers=[{"code": " d1 ", "name": "x"}],
        Signals=[{"code": "s 1", "driver": "d1", "name": "x", "tier": "a", "polarity": "higher IS better"}],
        Base_case=[])))
    assert sheet.errors == []
    assert sheet.signals[0]["code"] == "S1"
    assert sheet.signals[0]["tier"] == "A"
    assert sheet.signals[0]["polarity"] == "Higher is better"


def test_unknown_ids_are_errors(tmp_path):
    sheet = parse(build(tmp_path / "x.xlsx", **minimal(
        Signals=[{"code": "S1", "driver": "D9", "name": "x", "tier": "A"}],
        Base_case=[{"version": "v1", "case_type": "Consensus", "signal": "S7", "period": "Q1",
                    "value": 1, "source": "R9"}],
        Scoring_log=[{"date": dt.date(2026, 11, 1), "signal": "S1", "value": 1, "version": "v1",
                      "period": "Q1", "source": "R5"}])))
    errors = " | ".join(_msgs(sheet))
    for expected in ("Driver ID D9 is not defined", "Signal ID S7 is not defined",
                     "Source ID R9 is not defined", "Source ID R5 is not defined"):
        assert expected in errors


def test_bad_dropdown_and_number(tmp_path):
    sheet = parse(build(tmp_path / "x.xlsx", **minimal(
        Signals=[{"code": "S1", "driver": "D1", "name": "x", "tier": "A", "polarity": "Up is good",
                  "tolerance": "ten"}])))
    errors = " | ".join(_msgs(sheet))
    assert "Polarity 'Up is good' is not one of" in errors
    assert "Tolerance band must be a number" in errors


def test_percent_text_and_big_tolerance(tmp_path):
    sheet = parse(build(tmp_path / "x.xlsx", **minimal(
        Signals=[{"code": "S1", "driver": "D1", "name": "x", "tier": "A", "polarity": "Higher is better",
                  "tolerance": "10%"},
                 {"code": "S2", "driver": "D1", "name": "y", "tier": "A", "polarity": "Higher is better",
                  "tolerance": 10}])))
    assert sheet.signals[0]["tolerance"] == 0.1
    assert any("did you mean a fraction" in m for m in _msgs(sheet, "warning"))


def test_duplicates_are_errors(tmp_path):
    sheet = parse(build(tmp_path / "x.xlsx", **minimal(
        Drivers=[{"code": "D1", "name": "a"}, {"code": "D1", "name": "b"}],
        Base_case=[{"version": "v1", "case_type": "Consensus", "signal": "S1", "period": "Q1", "value": 1},
                   {"version": "V1", "case_type": "Consensus", "signal": "S1", "period": "q1", "value": 2}])))
    errors = " | ".join(_msgs(sheet))
    assert "duplicate Driver ID D1" in errors
    assert "duplicate base case" in errors


def test_driver_rule_warnings(tmp_path):
    sheet = parse(build(tmp_path / "x.xlsx", **minimal(
        Drivers=[{"code": "D1", "name": "a"}, {"code": "D2", "name": "b"}],
        Signals=[{"code": "S1", "driver": "D1", "name": "x", "tier": "C", "polarity": "Higher is better"}],
        Base_case=[])))
    warnings = " | ".join(_msgs(sheet, "warning"))
    assert "D1 has no Tier A or B signal" in warnings
    assert "D2 has no signals" in warnings


def test_scoring_row_without_matching_base_case_warns(tmp_path):
    sheet = parse(build(tmp_path / "x.xlsx", **minimal(
        Scoring_log=[{"date": dt.date(2026, 11, 1), "signal": "S1", "value": 1, "version": "v2",
                      "period": "Q3 FY26"}])))
    assert sheet.errors == []
    assert any("no Consensus base case for S1 v2" in m for m in _msgs(sheet, "warning"))


def test_wrong_file(tmp_path):
    import openpyxl
    p = tmp_path / "other.xlsx"
    openpyxl.Workbook().save(p)
    assert any("missing tabs" in m for m in _msgs(parse(p)))


def test_template_v2_fields(tmp_path):
    sheet = parse(build(tmp_path / "x.xlsx", **minimal(
        Drivers=[{"code": "D1", "name": "a", "type": "Mechanism", "share": 0.3},
                 {"code": "D2", "name": "b", "type": "option", "depends_on": "d1"}],
        Signals=[{"code": "S1", "driver": "D1", "name": "x", "tier": "A", "polarity": "Higher is better",
                  "star": "Y", "kill_switch": "N", "anchor": "Company guidance"},
                 {"code": "S2", "driver": "D2", "name": "y", "tier": "A", "polarity": "Higher is better"}],
        Event_ladder=[{"signal": "S1", "step": 1, "milestone": "Discloses Rubin share", "kind": "Disclosure"}],
        Scoring_log=[{"date": dt.date(2026, 11, 1), "signal": "S1", "version": "v1", "period": "Q3 FY26",
                      "withheld": "Y"}])))
    assert sheet.errors == [], sheet.errors
    assert [d["driver_type"] for d in sheet.drivers] == ["Mechanism", "Option"]
    assert sheet.drivers[1]["depends_on"] == "D1"
    assert sheet.signals[0]["binding_constraint"] is True and sheet.signals[1]["binding_constraint"] is False
    assert sheet.signals[0]["threshold_anchor"] == "Company guidance"
    assert sheet.event_ladder[0]["kind"] == "Disclosure"
    assert sheet.scores[0]["withheld"] is True


def test_template_v2_errors(tmp_path):
    sheet = parse(build(tmp_path / "x.xlsx", **minimal(
        Drivers=[{"code": "D1", "name": "a", "share": 1.5, "depends_on": "D9"}])))
    errors = " | ".join(_msgs(sheet))
    assert "Share of price must be between 0 and 1" in errors
    assert "Depends on D9: not a Driver ID" in errors


def test_sheet_writer_cli(tmp_path, capsys):
    import json

    from worker.sheet_writer import main as write_main

    spec = {"ticker": "NVDA", "owner_note": "Draft", "Drivers": [{"code": "D1", "name": "a", "type": "Core"}],
            "Signals": [{"code": "S1", "driver": "D1", "name": "x", "tier": "A", "polarity": "Higher is better"}],
            "Source log": [{"code": "R1", "url": "https://www.sec.gov/", "accessed": "2026-11-04"}],
            "Scoring log": [{"date": "2026-08-27", "signal": "S1", "value": 1, "version": "v1", "period": "Q2",
                             "source": "R1"}]}
    p = tmp_path / "spec.json"
    p.write_text(json.dumps(spec))
    assert write_main([str(p), str(tmp_path / "out.xlsx")]) == 0
    sheet = parse(tmp_path / "out.xlsx")
    assert sheet.scores[0]["observed_on"] == dt.date(2026, 8, 27)
    spec["Drivers"][0]["typo"] = 1
    p.write_text(json.dumps(spec))
    import pytest
    with pytest.raises(ValueError, match="unknown fields"):
        write_main([str(p), str(tmp_path / "out2.xlsx")])


def test_disclosure_step_on_numeric_signal_is_fine(tmp_path):
    sheet = parse(build(tmp_path / "x.xlsx", **minimal(
        Event_ladder=[{"signal": "S1", "step": 1, "milestone": "Discloses it", "kind": "Disclosure"},
                      {"signal": "S1", "step": 2, "milestone": "Plain step"}])))
    warnings = [m for m in _msgs(sheet, "warning") if "not 'Event ladder'" in m]
    assert len(warnings) == 1 and "row 3" in warnings[0]
