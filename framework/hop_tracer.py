from __future__ import annotations

import json
from typing import Any


def clip(value: Any, max_len: int = 400) -> str:
    s = value if isinstance(value, str) else json.dumps(value, indent=2, default=str)
    if s is None:
        return str(value)
    return s if len(s) <= max_len else s[:max_len] + f" …(+{len(s) - max_len} chars)"


def trace_hop(
    hop: int,
    text: str,
    tool_calls: list[tuple[str, Any]],
    tool_results: list[tuple[str, Any]],
    in_tok: int,
    out_tok: int,
    finish: str,
) -> None:
    bar = "─" * 52
    print(f"\n┌─ HOP {hop} {bar}")
    if text and text.strip():
        print(f"│ ← LLM   : {clip(text, 500)}")
    if tool_calls:
        for name, args in tool_calls:
            print(f"│ ⚙ CALL  : {name}({clip(args, 300)})")
    elif not (text and text.strip()):
        print("│ (no text, no tool call)")
    if tool_results:
        for name, out in tool_results:
            print(f"│ ⤷ RESULT: {name} → {clip(out, 400)}")
    print(f"│ • usage : {in_tok} in / {out_tok} out · finish={finish}")
    print(f"└{'─' * 60}")
