---
name: systematic-debugging
description: Four-phase systematic debugging methodology for Django applications. Use when diagnosing bugs, tracing data flow, or fixing production issues.
---

# Systematic Debugging

## Four Phases

1. **Reproduce and Investigate** — Create failing test, trace data flow
2. **Isolate** — Add strategic logging to narrow problem scope
3. **Identify Root Cause** — Examine stack traces, inspect application state
4. **Fix and Verify** — Implement solution, run full test suite

## Key Tools

- **Django Debug Toolbar** — N+1 query detection, slow queries (>10ms)
- **`breakpoint()`** — Pause execution and inspect variables
- **Query introspection** — Count queries to detect inefficiencies

## Common Problem Patterns

| Problem | Fix |
|---------|-----|
| N+1 queries | `select_related()` or `prefetch_related()` |
| Form validation failures | Check `is_valid()` and `form.errors` |
| CSRF errors | Verify form tokens present |
| Celery task issues | Run synchronously first to isolate |

## Quality Gate Before Closing

- Failing test now passes
- Full test suite green
- Type checking passes
- Linting clears

**Rule:** Never apply a quick fix without understanding the root cause. After three failed attempts, escalate to architecture discussion.
