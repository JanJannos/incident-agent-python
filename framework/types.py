from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

AgentEvent = dict[str, Any]
AgentEventHandler = Callable[[AgentEvent], None]
ToolBuilder = Callable[[dict[str, Any]], list]


@dataclass(frozen=True)
class AgentConfig:
    """Runtime knobs shared by all agents. Domain logic stays in each agent package."""

    name: str
    system_prompt: str
    build_tools: ToolBuilder
    model: str
    cheap_model: str
    capture_key: str
    max_steps: int = 8
    incomplete_error: str = "Agent did not produce a final result."


@dataclass
class AgentRunResult:
    input: str
    model: str
    output: Any
    steps: int
    tokens_used: dict[str, int]
    timing: dict[str, Any]
