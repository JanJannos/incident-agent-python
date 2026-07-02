"""SQLite connection management.

Port of src/db/client.ts. Opens the SAME sqlite database the incident-agent
seeds (read-only), i.e. `<project-root>/incident-agent/db/incidents.db`,
unless overridden via the INCIDENT_DB_PATH environment variable.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent

# incident-ui/src -> incident-ui -> <project-root> -> incident-agent/db/incidents.db
_DEFAULT_DB_PATH = (_THIS_DIR / ".." / ".." / "incident-agent" / "db" / "incidents.db").resolve()

_env_override = os.environ.get("INCIDENT_DB_PATH")
DB_PATH: Path = Path(_env_override).resolve() if _env_override else _DEFAULT_DB_PATH

_db: sqlite3.Connection | None = None


def get_db() -> sqlite3.Connection:
    """Return the cached, read-only SQLite connection, opening it on first call."""
    global _db
    if _db is None:
        if not DB_PATH.exists():
            raise RuntimeError(
                f'Database not found at {DB_PATH}. Run seed first.'
            )
        _db = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, check_same_thread=False)
        _db.row_factory = sqlite3.Row
        try:
            # Mirrors the TS `db.pragma('journal_mode = WAL')` call. On a
            # read-only handle this is a no-op if the DB is already in WAL
            # mode (set by the agent's seed script); ignore failures rather
            # than preventing the UI from opening the database.
            _db.execute("PRAGMA journal_mode = WAL")
        except sqlite3.Error:
            pass
    return _db


def close_db() -> None:
    """Close the cached connection, if any, and clear the singleton."""
    global _db
    if _db is not None:
        _db.close()
        _db = None
