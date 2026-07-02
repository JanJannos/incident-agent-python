"""Groq (OpenAI-compatible) tool-calling schema + dispatcher.

Port of src/tools/index.ts. The `TOOLSET` list is the JSON-schema tool
definitions passed to the Groq chat completions API; `execute_tool` mirrors
each tool's `execute` in the TS `toolset` (JSON-stringified with indent=2).
"""

from __future__ import annotations

import json
from typing import Any

import tools_impl

TOOLSET: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_events",
            "description": (
                "Get raw event log entries filtered by event_key, topic, or partition. "
                "Returns events ordered by offset."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "event_key": {
                        "type": "string",
                        "description": "The entity key (e.g. order_id) to filter by",
                    },
                    "topic": {
                        "type": "string",
                        "description": 'The topic name (e.g. "orders")',
                    },
                    "partition": {
                        "type": "number",
                        "description": "The partition number",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_entity_state",
            "description": (
                "Get the current persisted state of an entity (order, user, etc). "
                "Shows status, version, and last event processed."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_id": {
                        "type": "string",
                        "description": 'The entity ID to look up (e.g. "order_1000")',
                    },
                },
                "required": ["entity_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "replay_events",
            "description": (
                "Reconstruct the full event sequence for one entity_id. Shows which "
                "events were processed (idempotency check passed) and which were not."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "event_key": {
                        "type": "string",
                        "description": 'The entity key to replay events for (e.g. "order_1000")',
                    },
                },
                "required": ["event_key"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_idempotency",
            "description": (
                "Check whether a specific event was processed and recorded in the "
                "idempotency table. Returns processed status and timestamp."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "event_id": {
                        "type": "string",
                        "description": "The event ID (UUID) to check",
                    },
                },
                "required": ["event_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "diagnose",
            "description": (
                "TERMINAL TOOL: Commit to a final diagnosis of the incident. This ends "
                "the investigation. Provide bug_type (duplicate_event, ordering_violation, "
                "poison_pill, no_outbox, none), evidence summary, and recommended fix."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_id": {
                        "type": "string",
                        "description": "The entity ID being investigated",
                    },
                    "bug_type": {
                        "type": "string",
                        "enum": [
                            "duplicate_event",
                            "ordering_violation",
                            "poison_pill",
                            "no_outbox",
                            "none",
                        ],
                        "description": 'The type of bug detected, or "none" if no bug found',
                    },
                    "evidence": {
                        "type": "string",
                        "description": (
                            "Summary of evidence supporting this diagnosis "
                            "(what you observed)"
                        ),
                    },
                    "fix": {
                        "type": "string",
                        "description": "Recommended fix or mitigation for this issue",
                    },
                },
                "required": ["entity_id", "bug_type", "evidence", "fix"],
            },
        },
    },
]

TOOL_NAMES = {tool["function"]["name"] for tool in TOOLSET}


def execute_tool(name: str, args: dict[str, Any]) -> str:
    """Dispatch a tool call by name, returning a JSON string (indent=2) like the TS `execute` fns."""
    if name == "get_events":
        result = tools_impl.get_events(
            event_key=args.get("event_key"),
            topic=args.get("topic"),
            partition=args.get("partition"),
        )
        return json.dumps(result, indent=2)

    if name == "get_entity_state":
        state = tools_impl.get_entity_state(args["entity_id"])
        if state is None:
            return json.dumps({"error": "Entity not found"}, indent=2)
        return json.dumps(state, indent=2)

    if name == "replay_events":
        result = tools_impl.replay_events(args["event_key"])
        return json.dumps(result, indent=2)

    if name == "check_idempotency":
        result = tools_impl.check_idempotency(args["event_id"])
        return json.dumps(result, indent=2)

    if name == "diagnose":
        result = tools_impl.diagnose(
            entity_id=args["entity_id"],
            bug_type=args["bug_type"],
            evidence=args["evidence"],
            fix=args["fix"],
        )
        return json.dumps(
            {"status": "INVESTIGATION_COMPLETE", "diagnosis": result}, indent=2
        )

    raise ValueError(f"Unknown tool: {name}")
