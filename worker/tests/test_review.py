"""M3 review workflow: the queue preview, approve, edit-then-approve, reject, and who may do what."""

from __future__ import annotations

import json
import uuid

import pytest

OWNER, VIEWER = uuid.uuid4(), uuid.uuid4()


@pytest.fixture
def setup(db):
    for uid, role in ((OWNER, "owner"), (VIEWER, "viewer")):
        db.execute("insert into auth.users (id, email) values (%s, %s)", (uid, f"{role}@example.com"))
        db.execute("insert into members (user_id, email, role) values (%s, %s, %s)", (uid, f"{role}@example.com", role))
    db.execute("insert into tickers (symbol) values ('NVDA')")
    db.execute("insert into drivers (ticker, code, name) values ('NVDA', 'D1', 'Capex')")
    db.execute("insert into sources (ticker, code, url) values ('NVDA', 'R1', 'https://www.sec.gov/')")
    db.execute("""insert into signals (ticker, code, driver_code, name, tier, polarity, tolerance, max_staleness_days)
                  values ('NVDA', 'S1', 'D1', 'Capex $B', 'A', 'Higher is better', 0.10, 120)""")
    db.execute("""insert into base_case (ticker, version, case_type, signal_code, period, value)
                  values ('NVDA', 'v1', 'Consensus', 'S1', 'Q3 FY26', 100)""")
    return db


def propose(db, value=95, **extra):
    payload = {"observed_on": "2026-11-01", "value": value, "period": "Q3 FY26", "base_case_version": "v1",
               "source_code": "R1", "arrow": "Flat"} | extra
    return db.execute(
        "insert into proposals (kind, ticker, signal_code, payload, origin) "
        "values ('observation', 'NVDA', 'S1', %s, 'agent_web') returning id", (json.dumps(payload),)).fetchone()[0]


def as_user(db, uid):
    db.execute("set local role authenticated")
    db.execute("select set_config('request.jwt.claim.sub', %s, true)", (str(uid),))


def test_queue_previews_the_colour(setup):
    propose(setup, 95)
    row = setup.execute(
        "select preview_colour, preview_status, base_value, status from v_proposal_queue").fetchone()
    assert row == ("YELLOW", "OK", 100, "pending")


def test_approve_writes_observation_with_same_colour(setup):
    pid = propose(setup, 95)
    as_user(setup, OWNER)
    obs = setup.execute("select approve_proposal(%s)", (pid,)).fetchone()[0]
    assert setup.execute("select colour, origin, proposal_id from v_scores where observation_id = %s",
                         (obs,)).fetchone() == ("YELLOW", "proposal", pid)
    st, by = setup.execute("select status, reviewed_by from proposals where id = %s", (pid,)).fetchone()
    assert (st, by) == ("approved", OWNER)
    assert setup.execute("select count(*) from audit_log where table_name = 'observations' "
                         "and actor = %s", (OWNER,)).fetchone()[0] == 1


def test_edit_then_approve_keeps_original_payload(setup):
    pid = propose(setup, 95)
    as_user(setup, OWNER)
    obs = setup.execute("select approve_proposal(%s, %s, 'value corrected from 10-Q')",
                        (pid, json.dumps({"value": 120}))).fetchone()[0]
    assert setup.execute("select observed_value, colour from v_scores where observation_id = %s",
                         (obs,)).fetchone() == (120, "GREEN")
    orig, final, note = setup.execute(
        "select payload->>'value', approved_payload->>'value', reviewer_note from proposals where id = %s",
        (pid,)).fetchone()
    assert (orig, final, note) == ("95", "120", "value corrected from 10-Q")


def test_cannot_approve_twice(setup):
    pid = propose(setup)
    as_user(setup, OWNER)
    setup.execute("select approve_proposal(%s)", (pid,))
    with pytest.raises(Exception, match="already approved"):
        with setup.transaction():
            setup.execute("select approve_proposal(%s)", (pid,))


def test_reject_needs_a_reason(setup):
    pid = propose(setup)
    as_user(setup, OWNER)
    with pytest.raises(Exception, match="reason is required"):
        with setup.transaction():
            setup.execute("select reject_proposal(%s, '  ')", (pid,))
    setup.execute("select reject_proposal(%s, 'wrong period')", (pid,))
    assert setup.execute("select status, reviewer_note from proposals where id = %s", (pid,)).fetchone() == (
        "rejected", "wrong period")
    assert setup.execute("select count(*) from observations").fetchone()[0] == 0


def test_viewer_cannot_decide(setup):
    pid = propose(setup)
    as_user(setup, VIEWER)
    for sql in ("select approve_proposal(%s)", "select reject_proposal(%s, 'no')"):
        with pytest.raises(Exception, match="only reviewers and owners"):
            with setup.transaction():
                setup.execute(sql, (pid,))
    # No update policy: a direct status change touches no rows.
    cur = setup.execute("update proposals set status = 'approved' where id = %s", (pid,))
    assert cur.rowcount == 0
    setup.execute("reset role")
    assert setup.execute("select status from proposals where id = %s", (pid,)).fetchone()[0] == "pending"


def test_withheld_proposal_approves_to_red(setup):
    pid = propose(setup, None, withheld=True)
    as_user(setup, OWNER)
    obs = setup.execute("select approve_proposal(%s)", (pid,)).fetchone()[0]
    assert setup.execute("select colour, data_status from v_scores where observation_id = %s",
                         (obs,)).fetchone() == ("RED", "Withheld")


def test_missing_value_needs_withheld_flag(setup):
    pid = propose(setup, None)
    as_user(setup, OWNER)
    with pytest.raises(Exception, match="has no value"):
        with setup.transaction():
            setup.execute("select approve_proposal(%s)", (pid,))
