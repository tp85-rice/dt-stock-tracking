"""M4 feeds: XBRL parsing, TSMC report parsing, and the daily job (with stand-in adapters, no network)."""

from __future__ import annotations

import datetime as dt
import json

from worker import sec
from worker.adapters import Reading
from worker.adapters.tsmc import parse_report
from worker.run_feeds import run

IXBRL = """<html><body>
<xbrli:context id="q"><xbrli:entity/><xbrli:period><xbrli:startDate>2026-04-27</xbrli:startDate><xbrli:endDate>2026-07-26</xbrli:endDate></xbrli:period></xbrli:context>
<xbrli:context id="ytd"><xbrli:entity/><xbrli:period><xbrli:startDate>2026-01-26</xbrli:startDate><xbrli:endDate>2026-07-26</xbrli:endDate></xbrli:period></xbrli:context>
<xbrli:context id="i"><xbrli:entity/><xbrli:period><xbrli:instant>2026-07-26</xbrli:instant></xbrli:period></xbrli:context>
<xbrli:context id="qd"><xbrli:entity><xbrli:segment><xbrldi:explicitMember dimension="srt:ProductOrServiceAxis">nvda:AICloudsIndustrialEnterpriseMember</xbrldi:explicitMember></xbrli:segment></xbrli:entity><xbrli:period><xbrli:startDate>2026-04-27</xbrli:startDate><xbrli:endDate>2026-07-26</xbrli:endDate></xbrli:period></xbrli:context>
<ix:nonNumeric name="dei:DocumentFiscalPeriodFocus" contextRef="q">Q2</ix:nonNumeric>
<ix:nonNumeric name="dei:DocumentFiscalYearFocus" contextRef="q">2027</ix:nonNumeric>
<ix:nonFraction name="us-gaap:Revenues" contextRef="q" scale="6" decimals="-6">96,221</ix:nonFraction>
<ix:nonFraction name="us-gaap:Revenues" contextRef="ytd" scale="6" decimals="-6">177,837</ix:nonFraction>
<ix:nonFraction name="us-gaap:Revenues" contextRef="qd" scale="6" decimals="-6">40,313</ix:nonFraction>
<ix:nonFraction name="us-gaap:InventoryNet" contextRef="i" scale="6" decimals="-6">31,575</ix:nonFraction>
<ix:nonFraction name="us-gaap:SomeLoss" contextRef="q" scale="6" sign="-">12</ix:nonFraction>
</body></html>"""


def test_xbrl_facts_and_pick():
    facts = sec.xbrl_facts(IXBRL)
    end = dt.date(2026, 7, 26)
    assert sec.dei(facts, "DocumentFiscalPeriodFocus") == "Q2"
    assert sec.pick(facts, "us-gaap:Revenues", end, duration="quarter").value == 96_221_000_000
    assert sec.pick(facts, "us-gaap:Revenues", end, duration="ytd").value == 177_837_000_000
    assert sec.pick(facts, "us-gaap:Revenues", end, duration="quarter",
                    dims={"ProductOrServiceAxis": "AICloudsIndustrialEnterpriseMember"}).value == 40_313_000_000
    assert sec.pick(facts, "us-gaap:InventoryNet", end).value == 31_575_000_000
    assert sec.pick(facts, "us-gaap:SomeLoss", end, duration="quarter").value == -12_000_000


def test_tsmc_sentence():
    text = ("<p>TSMC September 2026 Revenue Report ... On a consolidated basis, revenue for September 2026 was "
            "approximately NT$511.86 billion, a decrease of 0.6 percent from August 2026 and an increase of 54.6 "
            "percent from September 2025.</p>")
    r = parse_report(text)
    assert (r["label"], r["yoy"]) == ("Sep 2026", 54.6)
    down = text.replace("an increase of 54.6", "a decrease of 3.2")
    assert parse_report(down)["yoy"] == -3.2


# ---------------------------------------------------------------- the daily job

def _seed(db, tmp_path):
    db.execute("insert into tickers (symbol) values ('NVDA'), ('TEST')")
    db.execute("update tickers set is_test = true where symbol = 'TEST'")
    for t in ("NVDA", "TEST"):
        db.execute("insert into drivers (ticker, code, name) values (%s, 'D1', 'x')", (t,))
        db.execute("""insert into signals (ticker, code, driver_code, name, polarity, tolerance)
                      values (%s, 'S7', 'D1', 'Inventory', 'Lower is better', 0.1)""", (t,))
    db.execute("insert into base_case (ticker, version, case_type, signal_code, period, value, snapshot_date) "
               "values ('NVDA', 'v2', 'Consensus', 'S7', 'Q3 FY27', 30, '2026-11-01')")
    feeds = tmp_path / "research"
    for t in ("NVDA", "TEST"):
        (feeds / t).mkdir(parents=True)
        (feeds / t / "feeds.json").write_text(json.dumps({"signals": {"S7": {"adapter": "fake", "params": {"k": 1}}}}))
    return feeds


def _fake(values):
    calls = []

    def adapter(ticker, signal, params):
        calls.append((ticker, signal, params))
        return [Reading(p, v, dt.date(2026, 11, 19), "https://www.sec.gov/x.htm", f"XBRL InventoryNet = {v}",
                        "NVDA 10-Q") for p, v in values]
    return adapter, calls


def test_job_proposes_once(db, tmp_path):
    feeds = _seed(db, tmp_path)
    fake, calls = _fake([("Q3 FY27", 33.1)])
    s = run(db, adapters={"fake": fake}, feed_root=feeds)
    assert s["proposed"] == ["NVDA S7 Q3 FY27 = 33.1"] and not s["errors"]
    assert calls == [("NVDA", "S7", {"k": 1})]          # test tickers are not fetched
    row = db.execute("select preview_colour, base_value, base_case_version, source_code, origin "
                     "from v_proposal_queue").fetchone()
    assert row == ("RED", 30, "v2", "R1", "fake")       # 33.1 vs 30 is 10.3% worse (> 10% tolerance); newest base case version; new source added
    assert db.execute("select url from sources where code = 'R1'").fetchone()[0] == "https://www.sec.gov/x.htm"
    # Second run: same period already proposed, nothing new.
    s = run(db, adapters={"fake": fake}, feed_root=feeds)
    assert s["proposed"] == [] and len(s["skipped"]) == 1
    assert db.execute("select count(*) from proposals").fetchone()[0] == 1
    assert db.execute("select status, n_proposals from runs order by id").fetchall() == [("succeeded", 1), ("succeeded", 0)]


def test_job_skips_periods_with_observations(db, tmp_path):
    feeds = _seed(db, tmp_path)
    db.execute("insert into observations (ticker, signal_code, value, period, base_case_version) "
               "values ('NVDA', 'S7', 31.575, 'Q2 FY27', 'v1')")
    fake, _ = _fake([("q2 fy27", 31.575), ("Q3 FY27", 33.1)])
    s = run(db, adapters={"fake": fake}, feed_root=feeds)
    assert s["proposed"] == ["NVDA S7 Q3 FY27 = 33.1"]


def test_rejected_periods_are_not_proposed_again(db, tmp_path):
    feeds = _seed(db, tmp_path)
    fake, _ = _fake([("Q3 FY27", 33.1)])
    run(db, adapters={"fake": fake}, feed_root=feeds)
    db.execute("update proposals set status = 'rejected', reviewer_note = 'wrong'")
    assert run(db, adapters={"fake": fake}, feed_root=feeds)["proposed"] == []


def test_broken_feed_is_reported_not_fatal(db, tmp_path):
    feeds = _seed(db, tmp_path)

    def broken(*_):
        raise RuntimeError("SEC is down")
    s = run(db, adapters={"fake": broken}, feed_root=feeds)
    assert s["errors"] == ["NVDA S7 (fake): SEC is down"]
    assert db.execute("select status, error from runs").fetchone() == ("failed", "NVDA S7 (fake): SEC is down")


def test_dry_run_writes_nothing(db, tmp_path):
    feeds = _seed(db, tmp_path)
    fake, _ = _fake([("Q3 FY27", 33.1)])
    s = run(db, dry_run=True, adapters={"fake": fake}, feed_root=feeds)
    assert s["proposed"] == ["NVDA S7 Q3 FY27 = 33.1"]
    assert db.execute("select (select count(*) from proposals) + (select count(*) from runs)").fetchone()[0] == 0


def test_unknown_signal_in_feeds_file_is_noted(db, tmp_path):
    feeds = _seed(db, tmp_path)
    (feeds / "NVDA" / "feeds.json").write_text(json.dumps({"signals": {"S99": {"adapter": "fake"}}}))
    s = run(db, adapters={}, feed_root=feeds)
    assert any("S99 is not in the database" in n for n in s["notes"])


def test_fetch_retries_timeouts_and_caches(monkeypatch):
    calls = []

    def flaky(url, timeout):
        calls.append(url)
        if len(calls) < 3:
            raise TimeoutError("The read operation timed out")
        return "ok"
    monkeypatch.setattr(sec, "_get", flaky)
    monkeypatch.setattr(sec, "BACKOFF", 0)
    monkeypatch.setattr(sec, "_cache", {})
    url = "https://www.sec.gov/Archives/edgar/data/1/x.htm"
    assert sec.fetch(url) == "ok" and len(calls) == 3      # two timeouts, then success
    assert sec.fetch(url) == "ok" and len(calls) == 3      # second read comes from the cache


def test_fetch_gives_up_after_retries(monkeypatch):
    import pytest

    def down(url, timeout):
        raise TimeoutError("down")
    monkeypatch.setattr(sec, "_get", down)
    monkeypatch.setattr(sec, "BACKOFF", 0)
    monkeypatch.setattr(sec, "_cache", {})
    with pytest.raises(TimeoutError):
        sec.fetch("https://www.sec.gov/cgi-bin/browse-edgar?x")


def test_numbers_inside_text_blocks_are_read():
    doc = IXBRL.replace(
        '<ix:nonFraction name="us-gaap:InventoryNet"',
        '<ix:nonNumeric name="us-gaap:InventoryDisclosureTextBlock" contextRef="q">Inventory note: '
        '<ix:nonFraction name="us-gaap:InventoryNet"').replace(
        '31,575</ix:nonFraction>', '31,575</ix:nonFraction> more text</ix:nonNumeric>')
    facts = sec.xbrl_facts(doc)
    assert sec.pick(facts, "us-gaap:InventoryNet", dt.date(2026, 7, 26)).value == 31_575_000_000


def test_fiscal_labels():
    from worker.financials import fiscal_label
    D = dt.date
    assert fiscal_label(D(2026, 7, 26), 1) == "Q2 FY27"
    assert fiscal_label(D(2026, 4, 26), 1) == "Q1 FY27"
    assert fiscal_label(D(2026, 1, 25), 1) == "Q4 FY26"
    assert fiscal_label(D(2026, 10, 25), 1) == "Q3 FY27"
    assert fiscal_label(D(2027, 1, 31), 1) == "Q4 FY27"
    assert fiscal_label(D(2026, 9, 30), 12) == "Q3 CY26"
    assert fiscal_label(D(2026, 12, 31), 12) == "Q4 CY26"
    assert fiscal_label(D(2026, 9, 30), 6) == "Q1 FY27"       # Microsoft: year ends in June


def test_fourth_quarter_is_derived_and_newest_filing_wins():
    from worker.financials import quarters_from_reports
    D = dt.date
    def F(v, s, e): return sec.Fact("us-gaap:Revenues", v, s, e, {})
    newest = [F(10.0, D(2026, 1, 26), D(2026, 4, 26))]                                  # Q1 FY27
    tenk = [F(100.0, D(2025, 1, 27), D(2026, 1, 25)),                                   # FY26 total
            F(20.0, D(2025, 7, 28), D(2025, 10, 26))]                                    # Q3 FY26
    older = [F(25.0, D(2025, 4, 28), D(2025, 7, 27)), F(30.0, D(2025, 1, 27), D(2025, 4, 27)),
             F(999.0, D(2025, 7, 28), D(2025, 10, 26))]                                  # stale Q3 (restated later)
    rows = quarters_from_reports([("new", newest), ("10k", tenk), ("old", older)],
                                 {"revenue": {"concept": "us-gaap:Revenues"}}, 1, 8)
    got = {r["fiscal_period"]: r["value"] for r in rows}
    assert got == {"Q1 FY27": 10.0, "Q4 FY26": 25.0, "Q3 FY26": 20.0, "Q2 FY26": 25.0, "Q1 FY26": 30.0}


def test_restated_previous_quarter_comes_from_six_month_figure():
    from worker.financials import quarters_from_reports
    D = dt.date
    def F(v, s, e): return sec.Fact("us-gaap:Revenues", v, s, e, {"ProductOrServiceAxis": "HyperscaleMember"})
    newest = [F(48.710, D(2026, 4, 27), D(2026, 7, 26)), F(91.761, D(2026, 1, 26), D(2026, 7, 26))]
    older = [F(37.869, D(2026, 1, 26), D(2026, 4, 26))]          # as first reported, before the recast
    rows = quarters_from_reports([("q2", newest), ("q1", older)],
                                 {"h": {"concept": "us-gaap:Revenues", "dims": {"ProductOrServiceAxis": "HyperscaleMember"}}}, 1, 8)
    got = {r["fiscal_period"]: round(r["value"], 3) for r in rows}
    assert got == {"Q2 FY27": 48.71, "Q1 FY27": 43.051}
