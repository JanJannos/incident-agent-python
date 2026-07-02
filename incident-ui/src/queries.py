"""Read-only helper queries used by the /api/tools endpoint.

Port of src/queries.ts. Ported EXACTLY as written, including the
`get_entity_state` quirk where it queries a table named `entities`
(distinct from the agent's `orders` table) — this is a pre-existing quirk
in the source project and is replicated faithfully here, not "fixed".
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return dict(row)


def get_events(
    db: sqlite3.Connection,
    params: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return event_log rows matching optional event_key/topic/partition filters."""
    query = "SELECT * FROM event_log WHERE 1=1"
    values: list[Any] = []

    event_key = params.get("event_key")
    topic = params.get("topic")
    partition = params.get("partition")

    if event_key:
        query += " AND event_key = ?"
        values.append(event_key)
    if topic:
        query += " AND topic = ?"
        values.append(topic)
    if partition is not None:
        query += " AND partition = ?"
        values.append(partition)

    query += " ORDER BY offset ASC"

    rows = db.execute(query, values).fetchall()

    result = []
    for row in rows:
        d = _row_to_dict(row)
        d["payload"] = json.loads(d["payload"])
        result.append(d)
    return result


def get_entity_state(
    db: sqlite3.Connection,
    params: dict[str, Any],
) -> dict[str, Any] | None:
    """Look up entity state.

    NOTE: this queries the `entities` table (not `orders`), matching the
    TS source exactly — a pre-existing quirk that is intentionally NOT
    fixed here.
    """
    row = db.execute(
        """SELECT entity_id, status, version, last_event_id, last_updated
           FROM entities
           WHERE entity_id = ?""",
        (params.get("entity_id"),),
    ).fetchone()
    return _row_to_dict(row) if row is not None else None


def replay_events(
    db: sqlite3.Connection,
    params: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return the full event history for an event_key, annotated with was_processed."""
    rows = db.execute(
        """SELECT
            e.id,
            e.event_type,
            e.offset,
            e.produced_at,
            e.payload,
            CASE WHEN p.event_id IS NOT NULL THEN 1 ELSE 0 END AS was_processed
          FROM event_log e
          LEFT JOIN processed_events p ON e.id = p.event_id
          WHERE e.event_key = ?
          ORDER BY e.offset ASC""",
        (params.get("event_key"),),
    ).fetchall()

    result = []
    for row in rows:
        d = _row_to_dict(row)
        result.append(
            {
                "id": d["id"],
                "event_type": d["event_type"],
                "offset": d["offset"],
                "produced_at": d["produced_at"],
                "payload": json.loads(d["payload"]),
                "was_processed": d["was_processed"] == 1,
            }
        )
    return result


def check_idempotency(
    db: sqlite3.Connection,
    params: dict[str, Any],
) -> dict[str, Any]:
    """Check whether a given event_id has already been processed."""
    event_id = params.get("event_id")
    row = db.execute(
        """SELECT event_id, processed_at
           FROM processed_events
           WHERE event_id = ?""",
        (event_id,),
    ).fetchone()

    return {
        "event_id": event_id,
        "was_processed": row is not None,
        "processed_at": row["processed_at"] if row is not None else None,
    }
