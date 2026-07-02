"""Flask port of src/server.ts.

Serves the copied `public/` frontend and a small JSON API backed by the
read-only incidents SQLite database, plus an SSE endpoint that streams
the incident-agent CLI's investigation events.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import time
from pathlib import Path
from typing import Any

from flask import Flask, Response, request, stream_with_context

import db_client
import queries as queries_mod
import run_agent
from query_validator import validate_read_only_query

THIS_DIR = Path(__file__).resolve().parent
PUBLIC_DIR = THIS_DIR.parent / "public"
PORT = int(os.environ.get("PORT") or 5000)

MIME = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
}

TABLE_NAME_RE = re.compile(r"^[a-z_]+$")

app = Flask(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return dict(row)


def send_json(data: Any, status: int = 200) -> Response:
    body = json.dumps(data, indent=2, default=str)
    resp = Response(body, status=status)
    resp.headers["Content-Type"] = "application/json; charset=utf-8"
    resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp


def send_error(status: int, message: str) -> Response:
    return send_json({"error": message}, status)


def parse_json_body() -> tuple[dict[str, Any] | None, Response | None]:
    """Parse the request body as JSON, mirroring the TS `JSON.parse(readBody(req))`.

    Returns (body_dict, None) on success, or (None, error_response) on failure.
    Non-object JSON values (arrays, numbers, etc.) are coerced to {} so that
    `.get()` lookups behave like optional-chained property access in JS.
    """
    raw = request.get_data(as_text=True) or ""
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None, send_error(400, "Invalid JSON body")
    if not isinstance(parsed, dict):
        parsed = {}
    return parsed, None


def list_tables(db: sqlite3.Connection) -> list[str]:
    rows = db.execute(
        """SELECT name FROM sqlite_master
           WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
           ORDER BY name"""
    ).fetchall()
    return [row["name"] for row in rows]


def table_exists(db: sqlite3.Connection, name: str) -> bool:
    row = db.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (name,),
    ).fetchone()
    return row is not None


# ---------------------------------------------------------------------------
# CORS / OPTIONS preflight (applies to every path, matching the TS server)
# ---------------------------------------------------------------------------


@app.before_request
def handle_options() -> Response | None:
    if request.method == "OPTIONS":
        resp = Response(status=204)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return resp
    return None


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------


@app.route("/api/meta", methods=["GET"])
def api_meta() -> Response:
    db = db_client.get_db()
    tables = []
    for name in list_tables(db):
        count_row = db.execute(f'SELECT COUNT(*) as count FROM "{name}"').fetchone()
        columns = [
            _row_to_dict(row)
            for row in db.execute(f'PRAGMA table_info("{name}")').fetchall()
        ]
        tables.append({"name": name, "rowCount": count_row["count"], "columns": columns})
    return send_json({"tables": tables, "dbPath": str(db_client.DB_PATH)})


@app.route("/api/entities", methods=["GET"])
def api_entities() -> Response:
    db = db_client.get_db()
    rows = db.execute(
        """SELECT o.entity_id, o.status, o.version, b.bug_type
           FROM orders o
           LEFT JOIN bugs b ON o.entity_id = b.entity_id
           ORDER BY o.entity_id"""
    ).fetchall()
    return send_json({"entities": [_row_to_dict(row) for row in rows]})


@app.route("/api/tables/<name>", methods=["GET"])
def api_table(name: str) -> Response:
    if not TABLE_NAME_RE.match(name):
        return send_error(404, "API route not found")

    db = db_client.get_db()
    if not table_exists(db, name):
        return send_error(404, f"Unknown table: {name}")

    def _to_int(raw: str | None, default: int) -> int:
        if raw is None:
            return default
        try:
            return int(raw)
        except (TypeError, ValueError):
            return default

    limit = min(_to_int(request.args.get("limit"), 100), 500)
    offset = _to_int(request.args.get("offset"), 0)

    rows = db.execute(
        f'SELECT * FROM "{name}" LIMIT ? OFFSET ?', (limit, offset)
    ).fetchall()
    total = db.execute(f'SELECT COUNT(*) as count FROM "{name}"').fetchone()

    return send_json(
        {
            "table": name,
            "rows": [_row_to_dict(row) for row in rows],
            "total": total["count"],
            "limit": limit,
            "offset": offset,
        }
    )


@app.route("/api/query", methods=["POST"])
def api_query() -> Response:
    body, err = parse_json_body()
    if err is not None:
        return err
    assert body is not None

    validation = validate_read_only_query(body.get("sql") or "")
    if not validation.get("ok"):
        return send_error(400, validation.get("error", "Invalid query"))

    db = db_client.get_db()
    sql = validation["sql"]
    try:
        started = time.monotonic()
        rows = db.execute(sql).fetchall()
        duration_ms = round((time.monotonic() - started) * 1000)
        return send_json(
            {
                "rows": [_row_to_dict(row) for row in rows],
                "rowCount": len(rows),
                "durationMs": duration_ms,
                "sql": sql,
            }
        )
    except sqlite3.Error as exc:
        return send_error(400, str(exc) or "Query failed")


@app.route("/api/tools", methods=["POST"])
def api_tools() -> Response:
    body, err = parse_json_body()
    if err is not None:
        return err
    assert body is not None

    tool = body.get("tool")
    params = body.get("params") or {}
    if not isinstance(params, dict):
        params = {}

    db = db_client.get_db()
    try:
        if tool == "get_events":
            result = queries_mod.get_events(db, params)
        elif tool == "get_entity_state":
            result = queries_mod.get_entity_state(db, params)
        elif tool == "replay_events":
            result = queries_mod.replay_events(db, params)
        elif tool == "check_idempotency":
            result = queries_mod.check_idempotency(db, params)
        else:
            return send_error(400, f"Unknown tool: {tool}")
    except Exception as exc:  # noqa: BLE001 - mirror TS catch(error)
        return send_error(400, str(exc) or "Tool call failed")

    return send_json({"tool": tool, "result": result})


@app.route("/api/investigate", methods=["POST"])
def api_investigate() -> Response:
    body, err = parse_json_body()
    if err is not None:
        return err
    assert body is not None

    entity_id = body.get("entityId")
    if not entity_id:
        return send_error(400, "entityId is required")

    cheap = bool(body.get("cheap", False))

    try:
        result = run_agent.run_agent_investigation(entity_id, cheap)
    except Exception as exc:  # noqa: BLE001 - mirror TS catch(error)
        return send_error(500, str(exc) or "Investigation failed")

    return send_json(result)


@app.route("/api/investigate/stream", methods=["GET"])
def api_investigate_stream() -> Response:
    entity_id = request.args.get("entityId")
    cheap = request.args.get("cheap") == "1"

    if not entity_id:
        return send_error(400, "entityId is required")

    def generate():
        def sse(event: Any) -> str:
            return f"data: {json.dumps(event)}\n\n"

        gen = run_agent.iter_agent_events(entity_id, cheap, heartbeat_interval=15.0)
        try:
            for kind, payload in gen:
                if kind == "event":
                    yield sse(payload)
                elif kind == "log":
                    yield sse({"type": "log", "line": payload})
                elif kind == "error":
                    yield sse({"type": "error", "message": payload})
                elif kind == "heartbeat":
                    yield ": ping\n\n"
                elif kind == "done":
                    yield sse({"type": "done", "exitCode": payload})
        finally:
            gen.close()

    resp = Response(stream_with_context(generate()), mimetype="text/event-stream; charset=utf-8")
    resp.headers["Cache-Control"] = "no-cache"
    resp.headers["Connection"] = "keep-alive"
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["X-Accel-Buffering"] = "no"
    return resp


@app.errorhandler(404)
def handle_404(_err: Any) -> Response:
    return send_error(404, "API route not found" if request.path.startswith("/api/") else "Not found")


@app.errorhandler(Exception)
def handle_exception(err: Exception) -> Response:
    # Mirrors the TS top-level `handleApi` try/catch: a thrown handler error
    # (e.g. "Database not found") must not crash the process; return a JSON
    # 500 instead so any in-flight SSE investigations are unaffected.
    from werkzeug.exceptions import HTTPException

    if isinstance(err, HTTPException):
        return send_error(err.code or 500, err.description or "Error")
    return send_error(500, str(err) or "Internal error")


# ---------------------------------------------------------------------------
# Static file serving (everything not under /api/)
# ---------------------------------------------------------------------------


@app.route("/", methods=["GET"])
def serve_index() -> Response:
    return _serve_static_file(PUBLIC_DIR / "index.html")


@app.route("/<path:subpath>", methods=["GET"])
def serve_static(subpath: str) -> Response:
    if subpath.startswith("api/"):
        return send_error(404, "API route not found")
    # Mirror Node's `path.join(PUBLIC_DIR, pathname)`: concatenate then
    # normalize (no traversal guard beyond what the TS original has).
    file_path = Path(os.path.normpath(str(PUBLIC_DIR / subpath)))
    return _serve_static_file(file_path)


def _serve_static_file(file_path: Path) -> Response:
    try:
        content = file_path.read_bytes()
    except OSError:
        return send_error(404, "Not found")

    ext = file_path.suffix
    content_type = MIME.get(ext, "text/plain")
    resp = Response(content, status=200)
    resp.headers["Content-Type"] = content_type
    return resp


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


def main() -> None:
    print(f"\n\U0001f50d Incident DB UI running at http://localhost:{PORT}")
    print(f"   SQLite: {db_client.DB_PATH}")
    print("   Press Ctrl+C to stop\n")
    try:
        app.run(host="0.0.0.0", port=PORT, threaded=True, use_reloader=False)
    finally:
        db_client.close_db()


if __name__ == "__main__":
    main()
