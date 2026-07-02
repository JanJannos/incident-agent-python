---
name: celery-patterns
description: Celery task patterns for Django including idempotency, retry strategies, periodic tasks, and async workflow. Use when implementing background tasks, scheduling, or async processing.
---

# Celery Patterns

## Core Philosophy
- **Idempotent tasks**: Running a task twice produces the same result
- **Pass IDs, not objects**: Arguments must be JSON-serializable
- **Always handle failures**: Log errors, never swallow exceptions silently
- **Exponential backoff**: Use for external service retries

## Task Design
- Place tasks in `apps/<domain>/tasks.py`
- Use `@shared_task` for reusable tasks
- Use `bind=True` when needing access to task instance (retries, task ID)
- Add type hints to task signatures
- Log task start, completion, and failures
- Pass model PKs, not model instances

## Retry Strategies
- **Fixed delay**: Internal operations with predictable recovery
- **Exponential backoff**: External APIs that may rate-limit
- **No retry**: Validation errors, permanent failures

**Config:**
- `max_retries` based on acceptable total wait time
- `retry_jitter=True` to prevent thundering herd
- `retry_backoff_max` to cap maximum wait
- `autoretry_for` for automatic retry on specific exceptions

## Idempotency Patterns
- Check-before-process: query current state before processing
- Status field tracking with `select_for_update()` for race safety
- Unique constraints to prevent duplicate processing

## Periodic Tasks
- Configure in `config/celery.py` using `beat_schedule`
- Use `crontab()` for time-based schedules
- Keep periodic tasks lightweight; spawn subtasks for heavy work

## Commands
```bash
uv run celery -A config worker -l info
uv run celery -A config beat -l info
uv run celery -A config flower
```

## Anti-Patterns
- Passing model instances instead of IDs
- Non-idempotent operations without checks
- Silent exception handling (`except: pass`)
- Missing logging for task lifecycle
- Retry on permanent failures
