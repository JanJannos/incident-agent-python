"""Round-robin Groq API key manager with revocation persistence.

Port of src/config/groqKeyManager.ts. Keys are loaded from
`../../config/groq.keys` (relative to this file, i.e. the repo root's
`config/` directory, a sibling of the `incident-agent` package). State
(current round-robin index + revoked keys) persists to
`../../config/.groq-state.json`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent
KEYS_FILE = (_THIS_DIR / ".." / ".." / "config" / "groq.keys").resolve()
STATE_FILE = (_THIS_DIR / ".." / ".." / "config" / ".groq-state.json").resolve()


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
                self.revoked_keys = set(state.get("revokedKeys", []) or [])
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

            if key not in self.revoked_keys:
                return key
            attempts += 1

        raise RuntimeError("All Groq keys have been revoked")

    def mark_key_as_revoked(self, key: str) -> None:
        self.revoked_keys.add(key)
        self._save_state()
        print(f"\U0001f511 Key revoked: {key[:10]}...", file=sys.stderr)

    def get_available_key_count(self) -> int:
        return len(self.keys) - len(self.revoked_keys)

    def reset_revoked_keys(self) -> None:
        self.revoked_keys.clear()
        self.current_index = 0
        self._save_state()


key_manager = GroqKeyManager()
