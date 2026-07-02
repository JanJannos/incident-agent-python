# What's Inside

This repository is an **Incident Detective Agent**: an AI-powered troubleshooting tool for distributed, event-driven systems.

Instead of debugging source code directly, it investigates system evidence (event logs, offsets, entity state, idempotency records) to explain **what went wrong**, **why**, and **how to fix it**.

---

## What This Project Does

Given an entity ID (for example `order_1000`), the agent:

1. Connects to a seeded SQLite database that simulates a Kafka/RabbitMQ-style system.
2. Uses an LLM (Groq) with structured tools to inspect incident evidence.
3. Reconstructs event timelines and validates processing behavior.
4. Produces a final diagnosis with:
   - bug type
   - evidence summary
   - recommended fix
5. Prints investigation stats (steps, token usage, runtime).

---

## Main Runtime Flow

### Entry point

- `run.sh`
  - Installs dependencies
  - Seeds DB
  - Runs investigation

### CLI

- `incident-agent/src/cli.ts`
  - Parses args (`entity_id`, optional `--cheap`)
  - Calls `runInvestigation()`
  - Prints the final report and token summary

### Investigation engine

- `incident-agent/src/agent/runInvestigation.ts`
  - Picks Groq model:
    - default: `llama-3.3-70b-versatile`
    - cheap mode: `llama-3.1-8b-instant`
  - Gets an API key via key manager (round-robin rotation)
  - Runs `generateText()` with:
    - system prompt
    - user prompt (`Investigate entity_id: ...`)
    - toolset
    - max 8 tool-calling steps
  - Expects terminal output from `diagnose()` (`INVESTIGATION_COMPLETE`)
  - Returns structured `InvestigationResult`

---

## Agent Behavior Rules

- `incident-agent/src/agent/systemPrompt.ts`
  - Forces evidence-based debugging behavior
  - Requires use of `replay_events` before conclusions
  - Requires `diagnose()` exactly once as the terminal action
  - Limits analysis to known bug classes:
    - `duplicate_event`
    - `ordering_violation`
    - `poison_pill`
    - `no_outbox`
    - `none`

---

## Tools the LLM Can Use

Defined in `incident-agent/src/tools/index.ts`:

- `get_events`  
  Query raw events by key/topic/partition.

- `get_consumer_offsets`  
  Inspect committed vs latest offset and lag.

- `get_entity_state`  
  Read current persisted state for an entity.

- `replay_events`  
  Rebuild event timeline and whether each event was processed.

- `check_idempotency`  
  Verify if an event exists in idempotency keys table.

- `diagnose` (terminal tool)  
  Commits final diagnosis and ends investigation loop.

---

## Data Layer and Simulation

### DB bootstrap

- `incident-agent/src/db/client.ts`
  - Opens `incident-agent/db/incidents.db`
  - Applies schema from `incident-agent/db/schema.sql`

### Schema

`incident-agent/db/schema.sql` defines:

- `events` — simulated event stream
- `consumer_offsets` — lag/commit positions
- `entity_state` — downstream materialized state
- `idempotency_keys` — dedup records
- `expected_state` — ground truth for evaluation

### Seeded incidents

- `incident-agent/scripts/seed.ts`
  - Generates sample incidents:
    - 4 duplicate-event incidents (`order_1000` range)
    - 2 clean incidents (`order_2000` range)
  - Inserts events/state/offsets/idempotency rows

This gives the agent realistic evidence to investigate.

---

## Key Management

- `incident-agent/src/config/groqKeyManager.ts`
  - Loads keys from `config/groq.keys`
  - Rotates keys round-robin
  - Marks revoked keys and persists state in `config/.groq-state.json`
  - Skips revoked keys automatically on future runs

---

## Package Scripts

From `incident-agent/package.json`:

- `npm run build` — compile TypeScript
- `npm run dev` — watch mode
- `npm run seed` — seed simulated incidents DB
- `npm run investigate -- <id>` — run compiled investigator
- `npm run run -- <id>` — build + run
- `npm run score` — intended scoring command (script target currently missing)

---

## What This Is Good For

- Demonstrating AI tool-calling for incident response
- Testing distributed-systems reasoning in a controlled environment
- Practicing diagnosis workflows without running real Kafka/RabbitMQ infra
- Building a benchmark harness for incident classification quality

---

## Typical Usage

```bash
./run.sh
./run.sh order_1000
./run.sh order_1000 --cheap
```

Expected output includes:

- bug type
- evidence
- recommended fix
- investigation steps
- token usage
- elapsed time

