"""Row level security: who can see and change what.

These run as the 'anon' and 'authenticated' roles, the way Supabase runs
requests from the browser.
"""

from __future__ import annotations

import uuid

import pytest

OWNER, REVIEWER, VIEWER, STRANGER = (uuid.uuid4() for _ in range(4))


@pytest.fixture
def seeded(db):
    for uid, role in ((OWNER, "owner"), (REVIEWER, "reviewer"), (VIEWER, "viewer"), (STRANGER, None)):
        db.execute("insert into auth.users (id, email) values (%s, %s)", (uid, f"{uid}@example.com"))
        if role:
            db.execute("insert into members (user_id, email, role) values (%s, %s, %s)",
                       (uid, f"{uid}@example.com", role))
    for sym, is_test in (("NVDA", False), ("TEST", True)):
        db.execute("insert into tickers (symbol, is_test) values (%s, %s)", (sym, is_test))
        db.execute("insert into drivers (ticker, code, name) values (%s, 'D1', 'x')", (sym,))
        db.execute("insert into signals (ticker, code, driver_code, name) values (%s, 'S1', 'D1', 'x')", (sym,))
        db.execute("insert into observations (ticker, signal_code, value) values (%s, 'S1', 1)", (sym,))
    return db


def as_user(db, uid):
    db.execute("set local role authenticated")
    db.execute("select set_config('request.jwt.claim.sub', %s, true)", (str(uid),))


def as_anon(db):
    db.execute("set local role anon")


def visible(db, table):
    return sorted(r[0] for r in db.execute(f"select distinct ticker from {table}").fetchall())


def test_anon_sees_nothing(seeded):
    as_anon(seeded)
    with pytest.raises(Exception, match="permission denied"):
        with seeded.transaction():
            seeded.execute("select * from signals")


def test_stranger_sees_nothing(seeded):
    as_user(seeded, STRANGER)
    assert visible(seeded, "signals") == []
    assert seeded.execute("select count(*) from tickers").fetchone()[0] == 0
    assert seeded.execute("select count(*) from v_scores").fetchone()[0] == 0


def test_viewer_sees_real_tickers_only(seeded):
    as_user(seeded, VIEWER)
    assert visible(seeded, "signals") == ["NVDA"]
    assert visible(seeded, "v_scores") == ["NVDA"]
    assert seeded.execute("select count(*) from audit_log").fetchone()[0] == 0


def test_viewer_cannot_write(seeded):
    as_user(seeded, VIEWER)
    seeded.execute("update signals set name = 'hacked'")  # RLS filters it to zero rows
    with pytest.raises(Exception, match="row-level security"):
        with seeded.transaction():
            seeded.execute("insert into drivers (ticker, code, name) values ('NVDA', 'D9', 'x')")
    seeded.execute("reset role")
    assert seeded.execute("select count(*) from signals where name = 'hacked'").fetchone()[0] == 0


def test_reviewer_sees_test_tickers_and_can_propose(seeded):
    as_user(seeded, REVIEWER)
    assert visible(seeded, "signals") == ["NVDA", "TEST"]
    seeded.execute("insert into proposals (kind, ticker, signal_code, payload, origin) "
                   "values ('observation', 'NVDA', 'S1', %s, 'manual')",
                   ('{"observed_on": "2026-11-01", "value": 1, "period": "Q1", "base_case_version": "v1"}',))
    with pytest.raises(Exception, match="row-level security"):
        with seeded.transaction():  # malformed payload is refused
            seeded.execute("insert into proposals (kind, ticker, signal_code, payload, origin) "
                           "values ('observation', 'NVDA', 'S1', '{}', 'manual')")
    with pytest.raises(Exception, match="row-level security"):
        with seeded.transaction():
            seeded.execute("insert into proposals (kind, ticker, payload, origin) "
                           "values ('observation', 'NVDA', '{}', 'agent_web')")
    with pytest.raises(Exception, match="row-level security"):
        with seeded.transaction():
            seeded.execute("insert into observations (ticker, signal_code, value) values ('NVDA', 'S1', 2)")


def test_owner_can_edit_and_manage_members(seeded):
    as_user(seeded, OWNER)
    seeded.execute("insert into drivers (ticker, code, name) values ('NVDA', 'D2', 'y')")
    assert seeded.execute("select count(*) from members").fetchone()[0] == 3
    seeded.execute("update members set role = 'reviewer' where user_id = %s", (VIEWER,))


def test_members_see_only_themselves(seeded):
    as_user(seeded, VIEWER)
    assert seeded.execute("select count(*) from members").fetchone()[0] == 1
