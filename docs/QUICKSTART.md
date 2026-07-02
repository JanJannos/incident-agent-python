# Quick Start Guide

## Run

```bash
# Default (order_1000, 70B model)
./run.sh

# Custom entity
./run.sh order_5000

# Fast mode (8B model)
./run.sh order_1000 --cheap
```

Auto-creates a virtualenv, installs dependencies, and seeds the database.

## What Happens

1. Agent loads a Groq API key (round-robin rotation)
2. Investigates the entity in the database
3. Uses AI (Groq function-calling) to diagnose the issue
4. Returns bug type, evidence, and fix recommendation
5. Shows token usage and timing

## Example Output

```
📊 Starting investigation for order_1000 (model: llama-3.3-70b-versatile)
🔑 Using Groq key: gsk_Y5nhrSp... (6 keys available)

============================================================
📋 INVESTIGATION RESULT
============================================================
Entity ID: order_1000
Bug Type: duplicate_event
Evidence: A duplicate payment_confirmed event was processed...
Recommended Fix: Add an idempotency check keyed on event_id...
Stats: 5 steps, 2340 in / 1245 out
Time: 3210ms
```

## Key Features

✅ **Round-robin key rotation** - Automatically cycles through API keys
✅ **Revocation handling** - Skips revoked keys automatically
✅ **Persistent state** - Remembers revoked keys between runs
✅ **Token tracking** - Shows input/output token usage
✅ **Timing info** - Measures investigation duration

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "All keys revoked" | Add more keys to `config/groq.keys` |
| "No entities found" | Run `python scripts/seed.py` first |
| "API errors" | Check groq.keys file has valid keys |

## Commands

```bash
cd incident-agent
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
./.venv/bin/python scripts/seed.py            # Initialize database
./.venv/bin/python src/cli.py <id>            # Run investigation
./.venv/bin/python src/cli.py <id> --stream   # Emit NDJSON events for the UI
```

## Key Management

Keys are stored in `config/groq.keys` (one per line):
```
gsk_YOUR_KEY_1
gsk_YOUR_KEY_2
gsk_YOUR_KEY_3
```

Revoked keys are tracked in `config/.groq-state.json` (auto-created).

---

For full documentation, see [README.md](../README.md)
