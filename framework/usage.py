from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

_usage_log: list[dict[str, Any]] = []


def get_usage_log() -> list[dict[str, Any]]:
    return list(_usage_log)


def log_usage(model: str, input_tokens: int, output_tokens: int) -> None:
    _usage_log.append(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "model": model,
            "inputTokens": input_tokens,
            "outputTokens": output_tokens,
        }
    )
