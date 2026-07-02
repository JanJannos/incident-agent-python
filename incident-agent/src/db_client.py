"""SQLite connection management.

Port of src/db/client.ts. Opens the incidents database (relative to the
package root, i.e. `incident-agent/db/incidents.db`), enables WAL mode, and
applies db/schema.sql on first open. The connection is cached in a
module-level singleton, mirroring the TS `let db: Database.Database | null`.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent
DB_PATH = _THIS_DIR / ".." / "db" / "incidents.db"
SCHEMA_PATH = _THIS_DIR / ".." / "db" / "schema.sql"

_db: sqlite3.Connection | None = None


def get_db() -> sqlite3.Connection:
    """Return the cached SQLite connection, opening and initializing it on first call."""
    global _db
    if _db is None:
        _db = sqlite3.connect(str(DB_PATH))
        _db.row_factory = sqlite3.Row
        _db.execute("PRAGMA journal_mode = WAL")
        schema = SCHEMA_PATH.read_text(encoding="utf-8")
        _db.executescript(schema)
        _db.commit()
    return _db


def close_db() -> None:
    """Close the cached connection, if any, and clear the singleton."""
    global _db
    if _db is not None:
        _db.close()
        _db = None
