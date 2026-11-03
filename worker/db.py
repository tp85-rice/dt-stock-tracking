"""Database connection for the worker.

Reads DATABASE_URL from the environment (or a local .env file). Use Supabase's
*session pooler* connection string from GitHub Actions and most laptops: the
direct connection is IPv6-only.
"""

from __future__ import annotations

import os
from pathlib import Path

import psycopg


def load_dotenv(path: str | Path = ".env") -> None:
    """Minimal .env reader so the worker has no extra dependency for it."""
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def connect(url: str | None = None) -> psycopg.Connection:
    load_dotenv()
    url = url or os.environ.get("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL is not set. Copy .env.example to .env and fill it in.")
    # prepare_threshold=None: Supabase's transaction pooler does not support
    # prepared statements; harmless on a direct or session connection.
    return psycopg.connect(url, prepare_threshold=None)
