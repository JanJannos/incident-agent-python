#!/usr/bin/env python3
"""Seed the incidents database with sample data.

Port of scripts/seed.ts. Generates 4 `duplicate_event` incidents
(order_1000..order_1003) and 2 clean incidents (order_2000..order_2001),
matching the TS version's event sequences, offsets, timestamps, idempotency
insert rules, and version logic exactly.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, TypedDict

_THIS_DIR = Path(__file__).resolve().parent
DB_PATH = _THIS_DIR / ".." / "db" / "incidents.db"
SCHEMA_PATH = _THIS_DIR / ".." / "db" / "schema.sql"


class Event(TypedDict):
    id: str
    topic: str
    partition: int
    offset: int
    event_key: str
    event_type: str
    payload: dict[str, Any]
    produced_at: str
    consumer_group: str


class Incident(TypedDict):
    entity_id: str
    correct_status: str
    bug_type: str
    explanation: str
    events: list[Event]


db = sqlite3.connect(str(DB_PATH))
db.execute("PRAGMA journal_mode = WAL")

# Initialize schema
schema = SCHEMA_PATH.read_text(encoding="utf-8")
db.executescript(schema)

# Clear tables
db.executescript(
    """
    DELETE FROM event_log;
    DELETE FROM orders;
    DELETE FROM processed_events;
    DELETE FROM bugs;
    """
)


def generate_timestamp(offset: int) -> str:
    base = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    result = base + timedelta(seconds=offset)
    # Match JS Date#toISOString(): milliseconds + 'Z'.
    return result.strftime("%Y-%m-%dT%H:%M:%S.") + f"{result.microsecond // 1000:03d}Z"


def create_incident_with_duplicate_event(incident_num: int, topic_offset: int) -> Incident:
    entity_id = f"order_{1000 + incident_num}"
    events: list[Event] = []
    offset = topic_offset

    # order_created
    events.append(
        {
            "id": str(uuid.uuid4()),
            "topic": "orders",
            "partition": 0,
            "offset": offset,
            "event_key": entity_id,
            "event_type": "order_created",
            "payload": {"order_id": entity_id, "amount": 100, "items": 1},
            "produced_at": generate_timestamp(0),
            "consumer_group": "order-processor",
        }
    )
    offset += 1

    # payment_confirmed (first time)
    events.append(
        {
            "id": str(uuid.uuid4()),
            "topic": "orders",
            "partition": 0,
            "offset": offset,
            "event_key": entity_id,
            "event_type": "payment_confirmed",
            "payload": {"order_id": entity_id, "amount": 100, "confirmation_id": "conf_1"},
            "produced_at": generate_timestamp(5),
            "consumer_group": "order-processor",
        }
    )
    offset += 1

    # payment_confirmed (DUPLICATE - simulates producer retry)
    events.append(
        {
            "id": str(uuid.uuid4()),
            "topic": "orders",
            "partition": 0,
            "offset": offset,
            "event_key": entity_id,
            "event_type": "payment_confirmed",
            "payload": {"order_id": entity_id, "amount": 100, "confirmation_id": "conf_1"},
            "produced_at": generate_timestamp(6),
            "consumer_group": "order-processor",
        }
    )
    offset += 1

    # order_shipped
    events.append(
        {
            "id": str(uuid.uuid4()),
            "topic": "orders",
            "partition": 0,
            "offset": offset,
            "event_key": entity_id,
            "event_type": "order_shipped",
            "payload": {"order_id": entity_id, "tracking": "TRACK123"},
            "produced_at": generate_timestamp(10),
            "consumer_group": "order-processor",
        }
    )
    offset += 1

    return {
        "entity_id": entity_id,
        "correct_status": "shipped",
        "bug_type": "duplicate_event",
        "explanation": (
            f"Duplicate payment_confirmed event at offset {offset - 2}. Consumer "
            "processed both, causing version to increment twice and amount "
            "potentially double-counted. Missing idempotency check."
        ),
        "events": events,
    }


def create_clean_incident(incident_num: int, topic_offset: int) -> Incident:
    entity_id = f"order_{2000 + incident_num}"
    events: list[Event] = []
    offset = topic_offset

    events.append(
        {
            "id": str(uuid.uuid4()),
            "topic": "orders",
            "partition": 0,
            "offset": offset,
            "event_key": entity_id,
            "event_type": "order_created",
            "payload": {"order_id": entity_id, "amount": 150, "items": 2},
            "produced_at": generate_timestamp(0),
            "consumer_group": "order-processor",
        }
    )
    offset += 1

    events.append(
        {
            "id": str(uuid.uuid4()),
            "topic": "orders",
            "partition": 0,
            "offset": offset,
            "event_key": entity_id,
            "event_type": "payment_confirmed",
            "payload": {"order_id": entity_id, "amount": 150, "confirmation_id": "conf_clean"},
            "produced_at": generate_timestamp(5),
            "consumer_group": "order-processor",
        }
    )
    offset += 1

    events.append(
        {
            "id": str(uuid.uuid4()),
            "topic": "orders",
            "partition": 0,
            "offset": offset,
            "event_key": entity_id,
            "event_type": "order_shipped",
            "payload": {"order_id": entity_id, "tracking": "CLEAN123"},
            "produced_at": generate_timestamp(10),
            "consumer_group": "order-processor",
        }
    )
    offset += 1

    return {
        "entity_id": entity_id,
        "correct_status": "shipped",
        "bug_type": "none",
        "explanation": "Clean incident with no bugs. All events in order, no duplicates.",
        "events": events,
    }


# Generate incidents
incidents: list[Incident] = []
current_offset = 0

# 4 incidents with duplicate events
for i in range(4):
    incidents.append(create_incident_with_duplicate_event(i, current_offset))
    current_offset += 10

# 2 clean control incidents
for i in range(2):
    incidents.append(create_clean_incident(i, current_offset))
    current_offset += 10

print(f"Seeding {len(incidents)} incidents...")

insert_event_sql = """
    INSERT INTO event_log
    (id, topic, partition, offset, event_key, event_type, payload, produced_at, consumer_group)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

insert_idempotency_key_sql = """
    INSERT INTO processed_events (event_id, processed_at)
    VALUES (?, ?)
"""

insert_entity_state_sql = """
    INSERT INTO orders (entity_id, status, version, last_event_id, last_updated)
    VALUES (?, ?, ?, ?, ?)
"""

insert_expected_state_sql = """
    INSERT INTO bugs (entity_id, correct_status, bug_type, explanation)
    VALUES (?, ?, ?, ?)
"""

with db:
    for incident in incidents:
        last_event_id = ""
        event_count = 0

        for i, event in enumerate(incident["events"]):
            db.execute(
                insert_event_sql,
                (
                    event["id"],
                    event["topic"],
                    event["partition"],
                    event["offset"],
                    event["event_key"],
                    event["event_type"],
                    json.dumps(event["payload"]),
                    event["produced_at"],
                    event["consumer_group"],
                ),
            )

            # For duplicate_event incidents: skip idempotency insert for the second
            # occurrence of payment_confirmed.
            if incident["bug_type"] == "duplicate_event":
                is_duplicate_payment = (
                    event["event_type"] == "payment_confirmed"
                    and i > 0
                    and incident["events"][i - 1]["event_type"] == "payment_confirmed"
                    and incident["events"][i - 1]["event_key"] == event["event_key"]
                )

                if not is_duplicate_payment:
                    db.execute(
                        insert_idempotency_key_sql,
                        (event["id"], datetime.now(timezone.utc).isoformat()),
                    )
            else:
                # Clean incidents: all events are processed
                db.execute(
                    insert_idempotency_key_sql,
                    (event["id"], datetime.now(timezone.utc).isoformat()),
                )

            last_event_id = event["id"]
            event_count += 1

        # Insert entity state with version = number of unique events processed
        db.execute(
            insert_entity_state_sql,
            (
                incident["entity_id"],
                incident["correct_status"],
                event_count if incident["bug_type"] == "duplicate_event" else event_count - 1,
                last_event_id,
                datetime.now(timezone.utc).isoformat(),
            ),
        )

        # Insert expected state
        db.execute(
            insert_expected_state_sql,
            (
                incident["entity_id"],
                incident["correct_status"],
                incident["bug_type"],
                incident["explanation"],
            ),
        )

print(f"✓ Seeded {len(incidents)} incidents")
print("✓ Duplicate event incidents: 4")
print("✓ Clean control incidents: 2")
print(f"✓ Database: {DB_PATH}")

db.close()
