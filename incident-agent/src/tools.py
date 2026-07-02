"""Incident investigator tool definitions (ai-sdk wrappers)."""

from __future__ import annotations

from typing import Any

from ai_sdk import tool

import tools_impl
from framework.tools import capture_result, dumps_json

_BUG_TYPES = ["duplicate_event", "ordering_violation", "poison_pill", "no_outbox", "none"]


def build_tools(captured: dict[str, Any]) -> list:
    def get_events(event_key=None, topic=None, partition=None, **_):
        return dumps_json(
            tools_impl.get_events(event_key=event_key, topic=topic, partition=partition)
        )

    def get_entity_state(entity_id=None, **_):
        state = tools_impl.get_entity_state(entity_id)
        return dumps_json(state if state else {"error": "Entity not found"})

    def replay_events(event_key=None, **_):
        return dumps_json(tools_impl.replay_events(event_key))

    def check_idempotency(event_id=None, **_):
        return dumps_json(tools_impl.check_idempotency(event_id))

    def diagnose(entity_id=None, bug_type=None, evidence=None, fix=None, **_):
        result = tools_impl.diagnose(entity_id, bug_type, evidence, fix)
        return capture_result(captured, "diagnosis", result, "INVESTIGATION_COMPLETE")

    return [
        tool(
            name="get_events",
            description="Get raw event log entries filtered by event_key, topic, or partition. Returns events ordered by offset.",
            parameters={
                "type": "object",
                "properties": {
                    "event_key": {"type": "string", "description": "The entity key (e.g. order_id) to filter by"},
                    "topic": {"type": "string", "description": 'The topic name (e.g. "orders")'},
                    "partition": {"type": "number", "description": "The partition number"},
                },
            },
            execute=get_events,
        ),
        tool(
            name="get_entity_state",
            description="Get the current persisted state of an entity (order, user, etc). Shows status, version, and last event processed.",
            parameters={
                "type": "object",
                "properties": {
                    "entity_id": {
                        "type": "string",
                        "description": 'The entity ID to look up (e.g. "order_1000")',
                    }
                },
                "required": ["entity_id"],
            },
            execute=get_entity_state,
        ),
        tool(
            name="replay_events",
            description="Reconstruct the full event sequence for one entity_id. Shows which events were processed (idempotency check passed) and which were not.",
            parameters={
                "type": "object",
                "properties": {
                    "event_key": {
                        "type": "string",
                        "description": 'The entity key to replay events for (e.g. "order_1000")',
                    }
                },
                "required": ["event_key"],
            },
            execute=replay_events,
        ),
        tool(
            name="check_idempotency",
            description="Check whether a specific event was processed and recorded in the idempotency table. Returns processed status and timestamp.",
            parameters={
                "type": "object",
                "properties": {
                    "event_id": {"type": "string", "description": "The event ID (UUID) to check"}
                },
                "required": ["event_id"],
            },
            execute=check_idempotency,
        ),
        tool(
            name="diagnose",
            description="TERMINAL TOOL: Commit to a final diagnosis of the incident. This ends the investigation. Provide bug_type (duplicate_event, ordering_violation, poison_pill, no_outbox, none), evidence summary, and recommended fix.",
            parameters={
                "type": "object",
                "properties": {
                    "entity_id": {"type": "string", "description": "The entity ID being investigated"},
                    "bug_type": {
                        "type": "string",
                        "enum": _BUG_TYPES,
                        "description": 'The type of bug detected, or "none" if no bug found',
                    },
                    "evidence": {
                        "type": "string",
                        "description": "Summary of evidence supporting this diagnosis (what you observed)",
                    },
                    "fix": {"type": "string", "description": "Recommended fix or mitigation for this issue"},
                },
                "required": ["entity_id", "bug_type", "evidence", "fix"],
            },
            execute=diagnose,
        ),
    ]
