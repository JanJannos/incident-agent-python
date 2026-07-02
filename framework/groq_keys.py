"""Round-robin Groq API key manager with revocation persistence."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
KEYS_FILE = _REPO_ROOT / "config" / "groq.keys"
STATE_FILE = _REPO_ROOT / "config" / ".groq-state.json"


def _key_fingerprint(key: str) -> str:
    """Stable ID for revocation state — never persist full API keys on disk."""
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


class GroqKeyManager:
    """Round-robin key rotation with persisted revocation state."""

    def __init__(self) -> None:
        self.keys: list[str] = []
        self.current_index: int = 0
        self.revoked_keys: set[str] = set()
        self._load_keys()
        self._load_state()

    def _load_keys(self) -> None:
        try:
            content = KEYS_FILE.read_text(encoding="utf-8")
        except OSError as error:
            raise RuntimeError(
                f"Failed to load Groq keys from {KEYS_FILE}: {error}"
            ) from error

        self.keys = [
            line.strip()
            for line in content.split("\n")
            if line.strip() and line.strip().startswith("gsk_")
        ]

    def _load_state(self) -> None:
        try:
            if STATE_FILE.exists():
                content = STATE_FILE.read_text(encoding="utf-8")
                state = json.loads(content)
                self.current_index = state.get("currentIndex", 0) or 0
                raw_revoked = state.get("revokedKeys", []) or []
                self.revoked_keys = {
                    _key_fingerprint(item) if str(item).startswith("gsk_") else str(item)
                    for item in raw_revoked
                }
        except Exception:
            print("Could not load key state, starting fresh", file=sys.stderr)

    def _save_state(self) -> None:
        try:
            state = {
                "currentIndex": self.current_index,
                "revokedKeys": list(self.revoked_keys),
            }
            STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
        except Exception as error:
            print(f"Could not save key state: {error}", file=sys.stderr)

    def get_next_key(self) -> str:
        if not self.keys:
            raise RuntimeError("No Groq keys available")

        attempts = 0
        while attempts < len(self.keys):
            key = self.keys[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.keys)

            if _key_fingerprint(key) not in self.revoked_keys:
                return key
            attempts += 1

        raise RuntimeError("All Groq keys have been revoked")

    def mark_key_as_revoked(self, key: str) -> None:
        self.revoked_keys.add(_key_fingerprint(key))
        self._save_state()
        print(f"\U0001f511 Key revoked: {key[:10]}...", file=sys.stderr)

    def get_available_key_count(self) -> int:
        return len(self.keys) - len(self.revoked_keys)

    def reset_revoked_keys(self) -> None:
        self.revoked_keys.clear()
        self.current_index = 0
        self._save_state()


key_manager = GroqKeyManager()
