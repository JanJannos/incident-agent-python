"""Incident investigator — domain logic only (not in framework)."""

from __future__ import annotations

from typing import Any, Optional, TypedDict

from framework.runner import run_agent
from framework.types import AgentConfig, AgentEvent, AgentEventHandler
from system_prompt import SYSTEM_PROMPT
from tools import build_tools

INCIDENT_CONFIG = AgentConfig(
    name="incident investigation",
    system_prompt=SYSTEM_PROMPT,
    build_tools=build_tools,
    model="llama-3.3-70b-versatile",
    cheap_model="llama-3.1-8b-instant",
    capture_key="diagnosis",
    max_steps=8,
    incomplete_error="Investigation did not complete with a valid diagnosis.",
)


class Diagnosis(TypedDict):
    entity_id: str
    bug_type: str
    evidence: str
    fix: str


class InvestigationResult(TypedDict):
    entityId: str
    diagnosis: Diagnosis
    steps: int
    tokensUsed: dict[str, int]
    timing: dict[str, Any]


def _ui_events(handler: Optional[AgentEventHandler]) -> Optional[AgentEventHandler]:
    """Map generic framework events to this agent's UI/CLI contract."""
    if handler is None:
        return None

    def forward(event: AgentEvent) -> None:
        if event.get("type") == "start" and "input" in event:
            event = {**event, "entityId": event["input"]}
        handler(event)

    return forward


def run_investigation(
    entity_id: str,
    cheap: bool = False,
    on_event: Optional[AgentEventHandler] = None,
) -> InvestigationResult:
    run = run_agent(
        INCIDENT_CONFIG,
        f"Investigate entity_id: {entity_id}",
        session_input=entity_id,
        cheap=cheap,
        on_event=_ui_events(on_event),
    )
    result: InvestigationResult = {
        "entityId": entity_id,
        "diagnosis": run.output,
        "steps": run.steps,
        "tokensUsed": run.tokens_used,
        "timing": run.timing,
    }
    if on_event:
        on_event({"type": "result", "result": result})
    return result
