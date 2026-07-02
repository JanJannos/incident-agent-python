"""Read-only SQL query validation.

Port of src/queryValidator.ts.
"""

from __future__ import annotations

import re
from typing import TypedDict

FORBIDDEN = [
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "CREATE",
    "REPLACE",
    "ATTACH",
    "DETACH",
    "PRAGMA",
    "VACUUM",
    "REINDEX",
]

_LINE_COMMENT_RE = re.compile(r"--.*$", re.MULTILINE)
_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)


class ValidationResult(TypedDict, total=False):
    ok: bool
    sql: str
    error: str


def validate_read_only_query(sql: str) -> ValidationResult:
    """Validate that `sql` is a single, read-only SELECT/WITH statement.

    Mirrors the TS discriminated union `{ ok: true; sql } | { ok: false; error }`.
    """
    stripped = _BLOCK_COMMENT_RE.sub("", _LINE_COMMENT_RE.sub("", sql)).strip()

    if not stripped:
        return {"ok": False, "error": "Query is empty"}

    statements = [part.strip() for part in stripped.split(";") if part.strip()]

    if len(statements) > 1:
        return {"ok": False, "error": "Only one SQL statement is allowed"}

    normalized = statements[0]
    upper = normalized.upper()

    if not upper.startswith("SELECT") and not upper.startswith("WITH"):
        return {"ok": False, "error": "Only SELECT queries are allowed"}

    for keyword in FORBIDDEN:
        if re.search(rf"\b{keyword}\b", normalized, re.IGNORECASE):
            return {"ok": False, "error": f"Forbidden keyword: {keyword}"}

    return {"ok": True, "sql": normalized}
