from __future__ import annotations


def _err_text(error: Exception) -> str:
    parts = [str(error), repr(error)]
    for attr in ("status_code", "code", "body", "message", "response"):
        value = getattr(error, attr, None)
        if value is not None:
            parts.append(str(value))
    return " ".join(parts).lower()


def is_rate_limited(error: Exception) -> bool:
    text = _err_text(error)
    return "429" in text or "rate_limit" in text or "rate limit" in text


def is_revoked(error: Exception) -> bool:
    text = _err_text(error)
    return (
        "401" in text
        or "invalid_api_key" in text
        or "invalid api key" in text
        or "revoked" in text
    )


def is_tool_use_failed(error: Exception) -> bool:
    return "tool_use_failed" in _err_text(error)
