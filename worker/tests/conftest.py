"""Shared test setup.

Database tests need a Postgres server. Point TEST_DATABASE_URL at one
(e.g. postgresql://postgres:postgres@localhost:5432/postgres). Each test run
creates a fresh throwaway database, applies the Supabase stand-in and every
migration in supabase/migrations/, and drops it at the end. Each test runs
inside a transaction that is rolled back, so tests never see each other's data.

NEVER point TEST_DATABASE_URL at the real Supabase project.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path

import psycopg
import pytest
from psycopg.conninfo import conninfo_to_dict, make_conninfo

REPO = Path(__file__).resolve().parents[2]
MIGRATIONS = sorted((REPO / "supabase" / "migrations").glob("*.sql"))
SHIM = Path(__file__).parent / "sql" / "supabase_shim.sql"
TODAY = "2026-11-03"  # pinned "today" for staleness and event-ladder tests


@pytest.fixture(scope="session")
def db_url():
    base = os.environ.get("TEST_DATABASE_URL")
    if not base:
        pytest.skip("TEST_DATABASE_URL not set; skipping database tests")
    if "supabase" in base:
        pytest.exit("TEST_DATABASE_URL points at Supabase. Use a local or CI Postgres.", returncode=2)
    name = f"dt_test_{uuid.uuid4().hex[:8]}"
    with psycopg.connect(base, autocommit=True) as admin:
        admin.execute(f'create database "{name}" encoding \'UTF8\' template template0')
    url = make_conninfo(**(conninfo_to_dict(base) | {"dbname": name}))
    try:
        with psycopg.connect(url, autocommit=True) as conn:
            conn.execute(SHIM.read_text())
            for m in MIGRATIONS:
                conn.execute(m.read_text())
        yield url
    finally:
        with psycopg.connect(base, autocommit=True) as admin:
            admin.execute(f'drop database if exists "{name}" with (force)')


@pytest.fixture
def db(db_url):
    """A connection inside a transaction that is always rolled back."""
    with psycopg.connect(db_url) as conn:
        with conn.transaction(force_rollback=True):
            conn.execute("select set_config('app.today', %s, true)", (TODAY,))
            yield conn
