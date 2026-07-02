#!/usr/bin/env python3
"""Command-line entry point.

Port of src/cli.ts. Runnable directly (`python src/cli.py <entity_id> [--cheap]
[--stream]`) from either the project root or the `incident-agent` directory --
this file inserts its own directory into `sys.path` so the sibling modules
(`run_investigation`, `db_client`, ...) import cleanly regardless of cwd.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_SRC_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SRC_DIR.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_SRC_DIR))

from db_client import close_db  # noqa: E402
from run_investigation import AgentEvent, get_usage_log, run_investigation  # noqa: E402

# Lines prefixed with this marker on stdout are structured events for the live
# UI (see incident-ui SSE endpoint). Kept distinct from human-readable logs.
EVENT_PREFIX = "__EVT__"


def main() -> None:
    args = sys.argv[1:]

    if len(args) == 0:
        print("Usage: python src/cli.py <entity_id>", file=sys.stderr)
        print("Example: python src/cli.py order_1000", file=sys.stderr)
        sys.exit(1)

    entity_id = args[0]
    use_cheap_model = "--cheap" in args
    stream_events = "--stream" in args

    def on_event(event: AgentEvent) -> None:
        sys.stdout.write(EVENT_PREFIX + json.dumps(event) + "\n")
        sys.stdout.flush()

    handler = on_event if stream_events else None

    try:
        result = run_investigation(entity_id, cheap=use_cheap_model, on_event=handler)

        print("\n" + "=" * 60)
        print("\U0001f4cb INVESTIGATION RESULT")
        print("=" * 60)
        print(f"Entity ID: {result['entityId']}")
        print(f"Bug Type: {result['diagnosis']['bug_type']}")
        print(f"\nEvidence:\n{result['diagnosis']['evidence']}")
        print(f"\nRecommended Fix:\n{result['diagnosis']['fix']}")
        print(
            f"\nStats: {result['steps']} steps, "
            f"{result['tokensUsed']['input']} in / {result['tokensUsed']['output']} out"
        )
        print(f"Time: {result['timing']['durationMs']}ms")
        print("=" * 60)

        # Print usage summary
        usage = get_usage_log()
        if usage:
            print("\n\U0001f4ca Token Usage Summary:")
            total_in = 0
            total_out = 0
            for entry in usage:
                total_in += entry["inputTokens"]
                total_out += entry["outputTokens"]
                print(f"  {entry['model']}: {entry['inputTokens']} in, {entry['outputTokens']} out")
            print(f"  TOTAL: {total_in} in, {total_out} out")
    except Exception as error:  # noqa: BLE001 - mirror TS's catch-all
        message = str(error) or "Investigation failed"
        if handler is not None:
            handler({"type": "error", "message": message})
        print(f"Investigation failed: {error}", file=sys.stderr)
        sys.exit(1)
    finally:
        close_db()


if __name__ == "__main__":
    main()
