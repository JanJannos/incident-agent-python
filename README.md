# Incident Detective Agent (Python)

AI agent that investigates bugs in distributed systems using Groq LLM. Analyzes database state, events, and Kafka offsets to diagnose problems.

Python port of the original Node.js/TypeScript project — same behavior, same tools, same live UI.

## Run

```bash
./run.sh                           # Default: order_1000 with 70B model
./run.sh order_1000                # Custom entity ID
./run.sh order_1000 --cheap        # Use 8B model (faster)
```

Auto-creates a virtualenv, installs dependencies, and seeds the database on first run.

## Live UI

```bash
./run-ui.sh                        # SQLite explorer + live agent stream at http://localhost:5000
```

## Config

Put Groq API keys in `config/groq.keys` (one per line):
```
gsk_KEY_1
gsk_KEY_2
gsk_KEY_3
```

Agent auto-rotates keys and skips revoked ones (state persisted in `config/.groq-state.json`).

## Manual commands

```bash
cd incident-agent
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
./.venv/bin/python scripts/seed.py            # Initialize database
./.venv/bin/python src/cli.py order_1000      # Run investigation
./.venv/bin/python src/cli.py order_1000 --cheap --stream   # Stream NDJSON events
```

## Layout

- `incident-agent/` — the agent: Groq function-calling loop, tools, SQLite data layer, CLI
- `incident-ui/` — Flask server: SQLite explorer + Server-Sent-Events live agent view
- `config/` — Groq API keys and rotation state
- `.claude/skills/` — reused engineering skills from the original project
