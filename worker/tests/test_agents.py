"""Agent plumbing (M5): quote check, scorecard scoring, review-queue submission and the daily cost cap."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import openpyxl
import pytest

from worker.agents import budget as budget_mod
from worker.agents.answers import schema_problems
from worker.agents.budget import Budget, BudgetExceeded, cost_usd
from worker.agents.checks import check, numbers_in, quote_found, value_in_quote
from worker.agents.evaluate import evaluate
from worker.agents.submit import submit

REPO = Path(__file__).resolve().parents[2]
SCORECARD = REPO / "templates" / "llm_eval_scorecard.xlsx"
SOURCE = "NVIDIA “CFO commentary”. Inventory was $31.6 billion,  up from $25.8 billion sequentially. More text."
QUOTE = 'Inventory was $31.6 billion, up from $25.8 billion sequentially'


# ---------------------------------------------------------------- checks

def test_quote_found_ignores_case_spacing_and_curly_quotes():
    assert quote_found(QUOTE.upper(), SOURCE)
    assert quote_found('NVIDIA "CFO commentary"', SOURCE)
    assert not quote_found("Inventory was $32.6 billion", SOURCE)
    assert not quote_found("NVIDIA", SOURCE)      # too short to mean anything
    assert not quote_found(QUOTE, None)


def test_numbers_and_value_in_quote():
    assert 31.6 in numbers_in(QUOTE) and 31.6e9 in numbers_in(QUOTE)
    assert numbers_in("revenue of $1,234.5 million") == [1234.5, 1234.5e6]
    assert value_in_quote(31.575, "$B", QUOTE)          # rounds to the quoted 31.6
    assert value_in_quote(31_600_000_000, None, QUOTE)  # raw dollars
    assert not value_in_quote(30.0, "$B", QUOTE)
    assert value_in_quote(73.5, "%", "gross margin was 73.5%")


def test_check_needs_source_text():
    a = {"value": 31.6, "unit": "$B", "quote": QUOTE}
    assert check(a, SOURCE)["passed"]
    r = check(a, None)
    assert not r["passed"] and "no source text" in r["reasons"][0]
    assert check(a | {"value": 40.0}, SOURCE)["reasons"] == ["value not found in the quote"]


def test_schema_problems():
    ok = {"case_id": "G1", "value": 1.0, "quote": "x"}
    assert schema_problems(ok, "evaluate") == []
    assert schema_problems({"case_id": "G1", "value": "1.0"}, "evaluate") == ["'value' must be a number or null"]
    assert "unknown key 'foo'" in schema_problems(ok | {"foo": 1}, "evaluate")
    assert schema_problems({"case_id": "G1"}, "evaluate") == ["no value or label, and not abstaining"]
    assert schema_problems({"case_id": "G1", "abstain": True}, "evaluate") == []
    assert schema_problems({"_parse_error": "line 3"}, "evaluate")[0].startswith("not valid JSON")


# ---------------------------------------------------------------- evaluation against the scorecard

GOLD = [
    # case, task, passage, answer, unit, period, entity, abstain
    ("G1", "KPI extraction", SOURCE, "31.6", "$B", "Q2 FY27", "NVIDIA", "N"),
    ("G2", "KPI extraction", "Data Center revenue was $41.1 billion.", "41.1", "$B", "Q2 FY27", "NVIDIA", "N"),
    ("G3", "KPI extraction", "The company did not give a figure.", "not in passage", None, None, None, "Y"),
    ("G4", "Event extraction", "NVIDIA raised its outlook for the year.", "guidance raise", None, None, None, "N"),
    ("G5", "KPI extraction", "Gross margin was 72.4%.", "72.4", "%", "Q2 FY27", None, "N"),
]
ANSWERS = [
    {"case_id": "G1", "value": 31.575, "unit": "$B", "period": "Q2 FY27", "entity": "NVIDIA Corporation", "quote": QUOTE},
    {"case_id": "G2", "value": 41.1, "unit": "$B", "period": "Q2 FY27", "entity": "NVIDIA",
     "quote": "Data Center revenue was $41.1 billion and rising"},                   # quote not in passage
    {"case_id": "G3", "value": 12.0, "quote": "The company did not give a figure."},  # should have abstained
    {"case_id": "G4", "label": "Guidance raise", "quote": "NVIDIA raised its outlook for the year."},
    # G5 missing
    {"case_id": "G9", "value": 1.0, "quote": "x"},                                    # unknown case
]


def _scorecard(tmp_path):
    path = tmp_path / "scorecard.xlsx"
    shutil.copy(SCORECARD, path)
    wb = openpyxl.load_workbook(path)
    ws = wb["Gold set"]
    for r, (cid, task, passage, ans, unit, period, entity, abstain) in enumerate(GOLD, start=2):
        for col, v in zip((1, 2, 7, 8, 9, 10, 11, 12, 13), (cid, "NVDA", passage, task, ans, unit, period, entity, abstain)):
            ws.cell(row=r, column=col).value = v
    wb.save(path)
    return path


def test_evaluate_scores_and_writes_runs(tmp_path):
    card = _scorecard(tmp_path)
    ans = tmp_path / "answers.jsonl"
    ans.write_text("\n".join(json.dumps(a) for a in ANSWERS) + "\nnot json\n")
    out = tmp_path / "scored.xlsx"
    res = evaluate(card, ans, "junior-v0.1", out)
    rows = {g[0]: r for g, r in zip(GOLD, res["rows"])}

    assert (rows["G1"]["value_ok"], rows["G1"]["citation_ok"], rows["G1"]["hallucination"]) == (1, 1, 0)
    assert (rows["G2"]["value_ok"], rows["G2"]["citation_ok"], rows["G2"]["hallucination"]) == (1, 0, 1)
    assert (rows["G3"]["value_ok"], rows["G3"]["hallucination"]) == (0, 1)
    assert (rows["G4"]["value_ok"], rows["G4"]["type_ok"]) == (1, 1)
    assert rows["G1"]["type_ok"] is None                                  # KPI task: no type check
    assert rows["G5"]["schema_ok"] == 0 and rows["G5"]["notes"] == "no answer for this case"
    assert res["unknown_case_ids"] == ["G9"]
    assert res["summary"]["overall"]["value_ok"] == pytest.approx(3 / 5)
    assert res["verdict"] == "FAIL"

    wb = openpyxl.load_workbook(out)
    ws = wb["Runs"]
    assert [ws.cell(row=r, column=2).value for r in range(2, 7)] == ["G1", "G2", "G3", "G4", "G5"]
    assert ws.cell(row=2, column=3).value == "junior-v0.1" and ws.cell(row=2, column=12).value == "auto"
    assert "person must confirm" in ws.cell(row=2, column=14).value
    assert wb["Summary"]["A10"].value == "junior-v0.1"
    # The original scorecard is untouched.
    assert openpyxl.load_workbook(card)["Runs"].cell(row=2, column=2).value is None


def test_evaluate_all_correct_passes(tmp_path):
    card = _scorecard(tmp_path)
    good = [ANSWERS[0],
            {"case_id": "G2", "value": 41.1, "unit": "$B", "period": "Q2 FY27", "entity": "NVIDIA",
             "quote": "Data Center revenue was $41.1 billion."},
            {"case_id": "G3", "abstain": True},
            ANSWERS[3],
            {"case_id": "G5", "value": 72.4, "unit": "%", "period": "q2 fy27", "quote": "Gross margin was 72.4%."}]
    ans = tmp_path / "answers.jsonl"
    ans.write_text("\n".join(json.dumps(a) for a in good))
    assert evaluate(card, ans, "v1")["verdict"] == "PASS"


# ---------------------------------------------------------------- budget

def test_cost_and_unknown_model():
    assert cost_usd("claude-sonnet-5-5", 1_000_000, 100_000) == pytest.approx(2.0 + 1.0)
    with pytest.raises(BudgetExceeded):
        cost_usd("claude-made-up", 10, 10)


def test_budget_in_memory():
    b = Budget(None, cap=0.05)
    b.reserve("claude-sonnet-5-5", 10_000, 1_000)        # up to $0.03
    b.record("claude-sonnet-5-5", 10_000, 1_000)
    with pytest.raises(BudgetExceeded):
        b.reserve("claude-sonnet-5-5", 10_000, 1_000)    # 0.03 + 0.03 > 0.05


def test_cap_from_env(monkeypatch):
    monkeypatch.setenv("AGENT_DAILY_USD_CAP", "2.5")
    assert Budget().cap == 2.5
    monkeypatch.delenv("AGENT_DAILY_USD_CAP")
    assert Budget().cap == budget_mod.DEFAULT_CAP_USD


def test_budget_counts_todays_agent_runs(db):
    db.execute("insert into runs (job, cost_usd) values ('agent_junior', 0.9), ('feeds', 5), ('agent_x', 0.05)")
    db.execute("insert into runs (job, cost_usd, started_at) values ('agent_old', 9, now() - interval '2 days')")
    b = Budget(db, cap=1.0)
    assert b.spent_today() == pytest.approx(0.95)
    with pytest.raises(BudgetExceeded):
        b.reserve("claude-opus-5-5", 10_000, 1_000)      # 0.06 more would pass 1.00
    b.run_id = db.execute("insert into runs (job) values ('agent_junior') returning id").fetchone()[0]
    b.record("claude-haiku-5-5", 1000, 100)
    row = db.execute("select input_tokens, output_tokens, cost_usd from runs where id = %s", (b.run_id,)).fetchone()
    assert row[:2] == (1000, 100) and float(row[2]) > 0


# ---------------------------------------------------------------- submission to the review queue

def _signals(db):
    db.execute("insert into tickers (symbol) values ('NVDA')")
    db.execute("insert into drivers (ticker, code, name) values ('NVDA', 'D6', 'Balance sheet')")
    db.execute("""insert into signals (ticker, code, driver_code, name, tier, unit, polarity, tolerance)
                  values ('NVDA', 'S7', 'D6', 'Inventory, $B', 'A', '$B', 'Lower is better', 0.1)""")


def _answer(**kw):
    a = {"ticker": "NVDA", "signal_code": "S7", "value": 31.575, "unit": "$B", "period": "Q2 FY27",
         "observed_on": "2026-08-26", "quote": QUOTE, "source_url": "https://example.com/cfo",
         "source_title": "CFO commentary", "source_text": SOURCE, "confidence": 0.9, "model": "claude-sonnet-5-5",
         "prompt_version": "junior-v0.1", "usage": {"input_tokens": 1000, "output_tokens": 100}, "_line": 1}
    return a | kw


def test_submit_dry_run_writes_nothing(db):
    _signals(db)
    out = submit(db, [_answer()], dry_run=True)
    assert out["proposed"] == ["NVDA S7 Q2 FY27 = 31.575"]
    assert db.execute("select count(*) from proposals").fetchone()[0] == 0
    assert db.execute("select count(*) from runs").fetchone()[0] == 0


def test_submit_adds_pending_and_held_proposals(db):
    _signals(db)
    out = submit(db, [
        _answer(),
        _answer(period="Q1 FY27", value=29.0),                    # value not in the quote -> held
        _answer(period="Q3 FY27", source_text=None),              # nothing to check against -> held
        _answer(signal_code="S99"),                               # not an owner-defined signal
        _answer(period="Q4 FY27", abstain=True, value=None),      # abstained
        {"ticker": "NVDA", "_line": 7},                           # bad shape
    ])
    assert len(out["proposed"]) == 1 and len(out["held_by_check"]) == 2
    assert len(out["errors"]) == 2 and any("not a defined signal" in e for e in out["errors"])
    assert out["skipped"] == ["NVDA S7 Q4 FY27 = None (agent abstained)"]
    rows = db.execute("""select status, origin, payload ->> 'period', check_result ->> 'passed', model, confidence
                         from proposals order by id""").fetchall()
    assert [r[0] for r in rows] == ["pending", "rejected_by_check", "rejected_by_check"]
    assert rows[0][1] == "agent_junior" and rows[0][3] == "true" and rows[0][4] == "claude-sonnet-5-5"
    # The new source is logged as Tier C until a reviewer says otherwise.
    assert db.execute("select tier from sources where url = 'https://example.com/cfo'").fetchone() == ("C",)
    run = db.execute("select job, n_proposals, input_tokens from runs").fetchone()
    assert run == ("agent_submit", 1, 3000)
    # Shows in the review queue with the agent's citation.
    q = db.execute("select origin, preview_status from v_proposal_queue where status = 'pending'").fetchone()
    assert q == ("agent_junior", "No base case")
    # A second submission of the same reading is skipped.
    again = submit(db, [_answer()])
    assert again["proposed"] == [] and "already recorded" in again["skipped"][0]
