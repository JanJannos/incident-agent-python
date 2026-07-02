"""Spawn the incident-agent CLI and collect/stream its output.

Port of src/runAgent.ts. Unlike the TS original (which shells out to
`npm run ...` inside the Node agent project), this spawns the Python agent
CLI directly:

    <python> <project-root>/incident-agent/src/cli.py <entityId> [--cheap] [--stream]

using the agent's own virtualenv interpreter when available.
"""

from __future__ import annotations

import json
import queue
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any, Iterator

# incident-ui/src -> incident-ui -> <project-root>
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
AGENT_ROOT = _PROJECT_ROOT / "incident-agent"
AGENT_CLI = AGENT_ROOT / "src" / "cli.py"
AGENT_VENV_PYTHON = AGENT_ROOT / ".venv" / "bin" / "python"

# Must match EVENT_PREFIX in incident-agent/src/cli.py
EVENT_PREFIX = "__EVT__"


def _agent_python() -> str:
    """Return the interpreter to run the agent CLI with."""
    if AGENT_VENV_PYTHON.exists():
        return str(AGENT_VENV_PYTHON)
    return sys.executable


def _build_command(entity_id: str, cheap: bool, stream: bool) -> list[str]:
    cmd = [_agent_python(), str(AGENT_CLI), entity_id]
    if cheap:
        cmd.append("--cheap")
    if stream:
        cmd.append("--stream")
    return cmd


def run_agent_investigation(entity_id: str, cheap: bool = False) -> dict[str, Any]:
    """Run the agent CLI to completion and return its combined output.

    Raises RuntimeError with the combined output (or a generic message) if
    the process exits with a non-zero code, mirroring the TS Promise
    rejection behavior.
    """
    cmd = _build_command(entity_id, cheap, stream=False)

    try:
        proc = subprocess.run(
            cmd,
            cwd=str(AGENT_ROOT),
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        raise RuntimeError(str(exc)) from exc

    stdout = proc.stdout or ""
    stderr = proc.stderr or ""
    output = stdout + (f"\n{stderr}" if stderr else "")

    if proc.returncode == 0:
        return {"output": output.strip(), "exitCode": 0}

    message = output.strip() or f"Agent exited with code {proc.returncode}"
    raise RuntimeError(message)


def iter_agent_events(
    entity_id: str,
    cheap: bool = False,
    heartbeat_interval: float | None = 15.0,
) -> Iterator[tuple[str, Any]]:
    """Spawn the agent CLI in --stream mode and yield events as they arrive.

    Yields tuples of:
      ('event', obj)      - a parsed __EVT__ JSON payload
      ('log', str)        - a human-readable log line (stdout or stderr)
      ('error', str)      - the process failed to spawn
      ('heartbeat', None) - no output for `heartbeat_interval` seconds;
                             callers may use this to emit an SSE comment/ping
      ('done', code)      - the process exited (code may be None)

    If the generator is closed early (e.g. the SSE client disconnects),
    the subprocess is killed.
    """
    cmd = _build_command(entity_id, cheap, stream=True)

    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(AGENT_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
    except OSError as exc:
        yield ("error", str(exc))
        return

    q: "queue.Queue[tuple[str, Any] | None]" = queue.Queue()

    def _drain_stdout() -> None:
        assert proc.stdout is not None
        for raw_line in proc.stdout:
            line = raw_line.rstrip("\n")
            idx = line.find(EVENT_PREFIX)
            if idx != -1:
                payload = line[idx + len(EVENT_PREFIX):]
                try:
                    q.put(("event", json.loads(payload)))
                except json.JSONDecodeError:
                    pass  # ignore malformed event line
            elif line.strip():
                q.put(("log", line))
        q.put(None)

    def _drain_stderr() -> None:
        assert proc.stderr is not None
        for raw_line in proc.stderr:
            text = raw_line.strip()
            if text:
                q.put(("log", text))
        q.put(None)

    stdout_thread = threading.Thread(target=_drain_stdout, daemon=True)
    stderr_thread = threading.Thread(target=_drain_stderr, daemon=True)
    stdout_thread.start()
    stderr_thread.start()

    try:
        pending = 2
        while pending > 0:
            try:
                item = q.get(timeout=heartbeat_interval)
            except queue.Empty:
                yield ("heartbeat", None)
                continue
            if item is None:
                pending -= 1
                continue
            yield item

        proc.wait()
        yield ("done", proc.returncode)
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
