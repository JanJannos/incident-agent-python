"""Helpers for building ai-sdk tool execute handlers."""

from __future__ import annotations

import json
from typing import Any


def dumps_json(value: Any) -> str:
    return json.dumps(value, indent=2, default=str)


def capture_result(captured: dict[str, Any], key: str, result: Any, status: str) -> str:
    captured[key] = result
    return dumps_json({"status": status, key: result})
