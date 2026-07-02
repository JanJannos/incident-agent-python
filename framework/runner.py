"""Generic Groq tool-calling agent loop (ai-sdk-python)."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Optional

from ai_sdk import generate_text, openai

from framework.errors import is_rate_limited, is_revoked, is_tool_use_failed
from framework.groq_keys import key_manager
from framework.hop_tracer import trace_hop
from framework.types import AgentConfig, AgentEvent, AgentEventHandler, AgentRunResult
from framework.usage import log_usage

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
os.environ.setdefault("OPENAI_BASE_URL", GROQ_BASE_URL)


def run_agent(
    config: AgentConfig,
    prompt: str,
    *,
    session_input: str | None = None,
    cheap: bool = False,
    on_event: Optional[AgentEventHandler] = None,
) -> AgentRunResult:
    started_at = datetime.now(timezone.utc)
    model_name = config.cheap_model if cheap else config.model
    captured: dict[str, Any] = {}
    totals = {"input": 0, "output": 0, "hops": 0}
    display_input = session_input if session_input is not None else prompt

    def emit(event: AgentEvent) -> None:
        if on_event:
            try:
                on_event(event)
            except Exception:
                pass

    api_key = key_manager.get_next_key()

    print(f"\n📊 Starting {config.name} ({display_input}) (model: {model_name})")
    print(
        f"🔑 Using Groq key: {api_key[:10]}... "
        f"({key_manager.get_available_key_count()} keys available)"
    )
    emit(
        {
            "type": "start",
            "input": display_input,
            "model": model_name,
            "keysAvailable": key_manager.get_available_key_count(),
        }
    )
    emit(
        {
            "type": "key",
            "action": "using",
            "key": api_key[:10],
            "available": key_manager.get_available_key_count(),
        }
    )

    def on_step(*args: Any) -> None:
        step = next((a for a in args if hasattr(a, "tool_calls")), args[-1])
        usage = getattr(step, "usage", None)
        in_tok = getattr(usage, "prompt_tokens", 0) or 0
        out_tok = getattr(usage, "completion_tokens", 0) or 0
        totals["input"] += in_tok
        totals["output"] += out_tok
        totals["hops"] += 1

        calls = [
            (getattr(c, "tool_name", ""), getattr(c, "args", {}))
            for c in (getattr(step, "tool_calls", None) or [])
        ]
        results = [
            (getattr(r, "tool_name", ""), getattr(r, "result", ""))
            for r in (getattr(step, "tool_results", None) or [])
        ]
        text = getattr(step, "text", "") or ""
        finish = getattr(step, "finish_reason", "") or ""

        trace_hop(totals["hops"], text, calls, results, in_tok, out_tok, finish)
        emit(
            {
                "type": "hop",
                "hop": totals["hops"],
                "toolCalls": [{"name": name, "args": args} for name, args in calls],
                "toolResults": [{"name": name, "output": output} for name, output in results],
                "text": text,
                "usage": {"input": in_tok, "output": out_tok},
                "finishReason": finish,
            }
        )

    def rotate_key() -> bool:
        nonlocal api_key
        previous = api_key
        try:
            api_key = key_manager.get_next_key()
        except Exception:
            return False
        if api_key == previous:
            return False
        print(
            f"🔁 Rotating to key {api_key[:10]}... "
            f"({key_manager.get_available_key_count()} available)"
        )
        emit(
            {
                "type": "key",
                "action": "rotating",
                "key": api_key[:10],
                "available": key_manager.get_available_key_count(),
            }
        )
        return True

    max_attempts = key_manager.get_available_key_count() + 2
    last_error: Optional[Exception] = None
    for attempt in range(1, max_attempts + 1):
        os.environ["OPENAI_BASE_URL"] = GROQ_BASE_URL
        model = openai(model_name, api_key=api_key)
        try:
            generate_text(
                model=model,
                system=config.system_prompt,
                prompt=prompt,
                tools=config.build_tools(captured),
                max_steps=config.max_steps,
                on_step=on_step,
            )
            break
        except Exception as error:  # noqa: BLE001
            last_error = error
            if is_revoked(error):
                print(f"❌ API key revoked: {api_key[:10]}...")
                emit(
                    {
                        "type": "notice",
                        "level": "error",
                        "code": "revoked",
                        "message": f"Key {api_key[:10]}… revoked",
                    }
                )
                key_manager.mark_key_as_revoked(api_key)
                if rotate_key():
                    continue
                raise
            if is_rate_limited(error):
                print(f"⏳ Rate limited on key {api_key[:10]}...")
                emit(
                    {
                        "type": "notice",
                        "level": "warn",
                        "code": "rate_limit",
                        "message": f"Rate limited on key {api_key[:10]}…",
                    }
                )
                if rotate_key():
                    continue
                raise
            if is_tool_use_failed(error) and attempt < max_attempts:
                print(
                    f"⚠️  Tool call generation failed "
                    f"(attempt {attempt}/{max_attempts}), retrying..."
                )
                emit(
                    {
                        "type": "notice",
                        "level": "warn",
                        "code": "tool_use_failed",
                        "message": (
                            f"Malformed tool call (attempt {attempt}/{max_attempts}), "
                            "retrying…"
                        ),
                    }
                )
                continue
            raise
    else:
        if last_error:
            raise last_error

    output = captured.get(config.capture_key)
    if output is None:
        raise RuntimeError(config.incomplete_error)

    completed_at = datetime.now(timezone.utc)
    duration_ms = int((completed_at - started_at).total_seconds() * 1000)
    log_usage(model_name, totals["input"], totals["output"])

    result = AgentRunResult(
        input=display_input,
        model=model_name,
        output=output,
        steps=totals["hops"],
        tokens_used={"input": totals["input"], "output": totals["output"]},
        timing={
            "startedAt": started_at.isoformat(),
            "completedAt": completed_at.isoformat(),
            "durationMs": duration_ms,
        },
    )
    return result
