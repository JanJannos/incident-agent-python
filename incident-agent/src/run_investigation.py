"""Incident investigation loop, built on the ai-sdk-python framework.

This is the Python analogue of the Node version's Vercel AI SDK usage: it drives
an agentic tool-calling loop with `ai_sdk.generate_text` (system prompt + tools +
`max_steps=8` + an `on_step` callback), talking to Groq through Groq's
OpenAI-compatible endpoint.

Public surface (imported by cli.py and the UI):
  - run_investigation(entity_id, cheap=False, on_event=None) -> InvestigationResult
  - get_usage_log() / log_usage()
  - AgentEvent / InvestigationResult types
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Callable, Optional, TypedDict

from ai_sdk import generate_text, openai, tool

from system_prompt import SYSTEM_PROMPT
import tools_impl

# Groq's OpenAI-compatible base URL. The ai-sdk-python `openai()` provider builds
# an `openai.OpenAI(api_key=...)` client with no base_url arg, but that client
# honors the OPENAI_BASE_URL env var — so we point it at Groq that way.
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
os.environ.setdefault("OPENAI_BASE_URL", GROQ_BASE_URL)

# Structured events forwarded to a live UI (same shapes as the Node AgentEvent
# union). Kept as a loose dict type — the UI/SSE layer json-encodes them.
AgentEvent = dict[str, Any]
AgentEventHandler = Callable[[AgentEvent], None]


class Diagnosis(TypedDict):
    entity_id: str
    bug_type: str
    evidence: str
    fix: str


class TokensUsed(TypedDict):
    input: int
    output: int


class Timing(TypedDict):
    startedAt: str
    completedAt: str
    durationMs: int


class InvestigationResult(TypedDict):
    entityId: str
    diagnosis: Diagnosis
    steps: int
    tokensUsed: TokensUsed
    timing: Timing


# ---------------------------------------------------------------------------
# Usage log
# ---------------------------------------------------------------------------
_usage_log: list[dict[str, Any]] = []


def get_usage_log() -> list[dict[str, Any]]:
    return _usage_log


def log_usage(model: str, input_tokens: int, output_tokens: int) -> None:
    _usage_log.append(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "model": model,
            "inputTokens": input_tokens,
            "outputTokens": output_tokens,
        }
    )


# ---------------------------------------------------------------------------
# Hop tracer (human-readable box printed to stdout, mirrors the Node hopTracer)
# ---------------------------------------------------------------------------
def _clip(value: Any, max_len: int = 400) -> str:
    s = value if isinstance(value, str) else json.dumps(value, indent=2, default=str)
    if s is None:
        return str(value)
    return s if len(s) <= max_len else s[:max_len] + f" …(+{len(s) - max_len} chars)"


def _trace_hop(hop: int, text: str, tool_calls: list, tool_results: list,
               in_tok: int, out_tok: int, finish: str) -> None:
    bar = "─" * 52
    print(f"\n┌─ HOP {hop} {bar}")
    if text and text.strip():
        print(f"│ ← LLM   : {_clip(text, 500)}")
    if tool_calls:
        for name, args in tool_calls:
            print(f"│ ⚙ CALL  : {name}({_clip(args, 300)})")
    elif not (text and text.strip()):
        print("│ (no text, no tool call)")
    if tool_results:
        for name, out in tool_results:
            print(f"│ ⤷ RESULT: {name} → {_clip(out, 400)}")
    print(f"│ • usage : {in_tok} in / {out_tok} out · finish={finish}")
    print(f"└{'─' * 60}")


# ---------------------------------------------------------------------------
# Error classification (framework-agnostic: match on status code / message text)
# ---------------------------------------------------------------------------
def _err_text(error: Exception) -> str:
    parts = [str(error), repr(error)]
    for attr in ("status_code", "code", "body", "message", "response"):
        v = getattr(error, attr, None)
        if v is not None:
            parts.append(str(v))
    return " ".join(parts).lower()


def _is_rate_limited(error: Exception) -> bool:
    t = _err_text(error)
    return "429" in t or "rate_limit" in t or "rate limit" in t


def _is_revoked(error: Exception) -> bool:
    t = _err_text(error)
    return "401" in t or "invalid_api_key" in t or "invalid api key" in t or "revoked" in t


def _is_tool_use_failed(error: Exception) -> bool:
    return "tool_use_failed" in _err_text(error)


# ---------------------------------------------------------------------------
# Tool construction — wrap tools_impl as ai_sdk tools. The diagnose tool also
# captures its result into `captured` so we don't depend on result introspection.
# ---------------------------------------------------------------------------
_BUG_TYPES = ["duplicate_event", "ordering_violation", "poison_pill", "no_outbox", "none"]


def _build_tools(captured: dict[str, Any]) -> list:
    def get_events(event_key=None, topic=None, partition=None, **_):
        return json.dumps(
            tools_impl.get_events(event_key=event_key, topic=topic, partition=partition),
            indent=2, default=str,
        )

    def get_entity_state(entity_id=None, **_):
        state = tools_impl.get_entity_state(entity_id)
        return json.dumps(state if state else {"error": "Entity not found"}, indent=2, default=str)

    def replay_events(event_key=None, **_):
        return json.dumps(tools_impl.replay_events(event_key), indent=2, default=str)

    def check_idempotency(event_id=None, **_):
        return json.dumps(tools_impl.check_idempotency(event_id), indent=2, default=str)

    def diagnose(entity_id=None, bug_type=None, evidence=None, fix=None, **_):
        result = tools_impl.diagnose(entity_id, bug_type, evidence, fix)
        captured["diagnosis"] = result
        return json.dumps({"status": "INVESTIGATION_COMPLETE", "diagnosis": result}, indent=2)

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
                "properties": {"entity_id": {"type": "string", "description": 'The entity ID to look up (e.g. "order_1000")'}},
                "required": ["entity_id"],
            },
            execute=get_entity_state,
        ),
        tool(
            name="replay_events",
            description="Reconstruct the full event sequence for one entity_id. Shows which events were processed (idempotency check passed) and which were not.",
            parameters={
                "type": "object",
                "properties": {"event_key": {"type": "string", "description": 'The entity key to replay events for (e.g. "order_1000")'}},
                "required": ["event_key"],
            },
            execute=replay_events,
        ),
        tool(
            name="check_idempotency",
            description="Check whether a specific event was processed and recorded in the idempotency table. Returns processed status and timestamp.",
            parameters={
                "type": "object",
                "properties": {"event_id": {"type": "string", "description": "The event ID (UUID) to check"}},
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
                    "bug_type": {"type": "string", "enum": _BUG_TYPES, "description": 'The type of bug detected, or "none" if no bug found'},
                    "evidence": {"type": "string", "description": "Summary of evidence supporting this diagnosis (what you observed)"},
                    "fix": {"type": "string", "description": "Recommended fix or mitigation for this issue"},
                },
                "required": ["entity_id", "bug_type", "evidence", "fix"],
            },
            execute=diagnose,
        ),
    ]


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
def run_investigation(
    entity_id: str,
    cheap: bool = False,
    on_event: Optional[AgentEventHandler] = None,
) -> InvestigationResult:
    from groq_key_manager import key_manager

    started_at = datetime.now(timezone.utc)
    model_name = "llama-3.1-8b-instant" if cheap else "llama-3.3-70b-versatile"

    def emit(event: AgentEvent) -> None:
        if on_event:
            try:
                on_event(event)
            except Exception:
                pass  # never let a UI listener break the investigation

    api_key = key_manager.get_next_key()

    print(f"\n📊 Starting investigation for {entity_id} (model: {model_name})")
    print(f"🔑 Using Groq key: {api_key[:10]}... ({key_manager.get_available_key_count()} keys available)")
    emit({"type": "start", "entityId": entity_id, "model": model_name,
          "keysAvailable": key_manager.get_available_key_count()})
    emit({"type": "key", "action": "using", "key": api_key[:10],
          "available": key_manager.get_available_key_count()})

    captured: dict[str, Any] = {}

    # Cross-attempt totals (true consumption, not just the winning run).
    totals = {"input": 0, "output": 0, "hops": 0}

    def on_step(*args: Any) -> None:
        # generate_text may call on_step as (step_index, result) or (result).
        step = next((a for a in args if hasattr(a, "tool_calls")), args[-1])
        usage = getattr(step, "usage", None)
        in_tok = getattr(usage, "prompt_tokens", 0) or 0
        out_tok = getattr(usage, "completion_tokens", 0) or 0
        totals["input"] += in_tok
        totals["output"] += out_tok
        totals["hops"] += 1

        calls = [(getattr(c, "tool_name", ""), getattr(c, "args", {})) for c in (getattr(step, "tool_calls", None) or [])]
        results = [(getattr(r, "tool_name", ""), getattr(r, "result", "")) for r in (getattr(step, "tool_results", None) or [])]
        text = getattr(step, "text", "") or ""
        finish = getattr(step, "finish_reason", "") or ""

        _trace_hop(totals["hops"], text, calls, results, in_tok, out_tok, finish)
        emit({
            "type": "hop",
            "hop": totals["hops"],
            "toolCalls": [{"name": n, "args": a} for n, a in calls],
            "toolResults": [{"name": n, "output": o} for n, o in results],
            "text": text,
            "usage": {"input": in_tok, "output": out_tok},
            "finishReason": finish,
        })

    def rotate_key() -> bool:
        nonlocal api_key
        previous = api_key
        try:
            api_key = key_manager.get_next_key()
        except Exception:
            return False
        if api_key == previous:
            return False
        print(f"🔁 Rotating to key {api_key[:10]}... ({key_manager.get_available_key_count()} available)")
        emit({"type": "key", "action": "rotating", "key": api_key[:10],
              "available": key_manager.get_available_key_count()})
        return True

    # Retry / rotation loop around the whole agentic call.
    #   429 rate_limit -> rotate + retry ; 401 revoked -> mark + rotate + retry
    #   tool_use_failed -> retry same key (model flake)
    max_attempts = key_manager.get_available_key_count() + 2
    last_error: Optional[Exception] = None
    for attempt in range(1, max_attempts + 1):
        os.environ["OPENAI_BASE_URL"] = GROQ_BASE_URL
        model = openai(model_name, api_key=api_key)
        try:
            generate_text(
                model=model,
                system=SYSTEM_PROMPT,
                prompt=f"Investigate entity_id: {entity_id}",
                tools=_build_tools(captured),
                max_steps=8,
                on_step=on_step,
            )
            break
        except Exception as error:  # noqa: BLE001
            last_error = error
            if _is_revoked(error):
                print(f"❌ API key revoked: {api_key[:10]}...")
                emit({"type": "notice", "level": "error", "code": "revoked",
                      "message": f"Key {api_key[:10]}… revoked"})
                key_manager.mark_key_as_revoked(api_key)
                if rotate_key():
                    continue
                raise
            if _is_rate_limited(error):
                print(f"⏳ Rate limited on key {api_key[:10]}...")
                emit({"type": "notice", "level": "warn", "code": "rate_limit",
                      "message": f"Rate limited on key {api_key[:10]}…"})
                if rotate_key():
                    continue
                raise
            if _is_tool_use_failed(error) and attempt < max_attempts:
                print(f"⚠️  Tool call generation failed (attempt {attempt}/{max_attempts}), retrying...")
                emit({"type": "notice", "level": "warn", "code": "tool_use_failed",
                      "message": f"Malformed tool call (attempt {attempt}/{max_attempts}), retrying…"})
                continue
            raise
    else:
        if last_error:
            raise last_error

    diagnosis = captured.get("diagnosis")
    if not diagnosis:
        raise RuntimeError("Investigation did not complete with a valid diagnosis.")

    completed_at = datetime.now(timezone.utc)
    duration_ms = int((completed_at - started_at).total_seconds() * 1000)

    log_usage(model_name, totals["input"], totals["output"])

    result: InvestigationResult = {
        "entityId": entity_id,
        "diagnosis": diagnosis,
        "steps": totals["hops"],
        "tokensUsed": {"input": totals["input"], "output": totals["output"]},
        "timing": {
            "startedAt": started_at.isoformat(),
            "completedAt": completed_at.isoformat(),
            "durationMs": duration_ms,
        },
    }
    emit({"type": "result", "result": result})
    return result
