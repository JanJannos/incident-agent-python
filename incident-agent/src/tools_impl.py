"""Plain query functions used by the incident investigator agent."""

from __future__ import annotations

import json
from typing import Any

from db_client import get_db


def get_events(
    event_key: str | None = None,
    topic: str | None = None,
    partition: int | None = None,
) -> list[dict[str, Any]]:
    db = get_db()

    query = "SELECT * FROM event_log WHERE 1=1"
    values: list[Any] = []

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

    return [
        {**dict(row), "payload": json.loads(row["payload"])}
        for row in rows
    ]


def get_entity_state(entity_id: str) -> dict[str, Any] | None:
    db = get_db()

    row = db.execute(
        """
        SELECT
          entity_id,
          status,
          version,
          last_event_id,
          last_updated
        FROM orders
        WHERE entity_id = ?
        """,
        (entity_id,),
    ).fetchone()

    return dict(row) if row is not None else None


def replay_events(event_key: str) -> list[dict[str, Any]]:
    db = get_db()

    rows = db.execute(
        """
        SELECT
          e.id,
          e.event_type,
          e.offset,
          e.produced_at,
          e.payload,
          CASE WHEN i.event_id IS NOT NULL THEN 1 ELSE 0 END as was_processed
        FROM event_log e
        LEFT JOIN processed_events i ON e.id = i.event_id
        WHERE e.event_key = ?
        ORDER BY e.offset ASC
        """,
        (event_key,),
    ).fetchall()

    return [
        {
            "id": row["id"],
            "event_type": row["event_type"],
            "offset": row["offset"],
            "produced_at": row["produced_at"],
            "payload": json.loads(row["payload"]),
            "was_processed": row["was_processed"] == 1,
        }
        for row in rows
    ]


def check_idempotency(event_id: str) -> dict[str, Any]:
    db = get_db()

    row = db.execute(
        """
        SELECT event_id, processed_at
        FROM processed_events
        WHERE event_id = ?
        """,
        (event_id,),
    ).fetchone()

    return {
        "event_id": event_id,
        "was_processed": row is not None,
        "processed_at": row["processed_at"] if row is not None else None,
    }


def diagnose(entity_id: str, bug_type: str, evidence: str, fix: str) -> dict[str, Any]:
    return {
        "entity_id": entity_id,
        "bug_type": bug_type,
        "evidence": evidence,
        "fix": fix,
    }
