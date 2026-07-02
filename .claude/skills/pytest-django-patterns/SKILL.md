---
name: pytest-django-patterns
description: pytest-django testing patterns, Factory Boy, fixtures, and TDD workflow. Use when writing tests, creating test factories, or following TDD red-green-refactor cycle.
---

# pytest-django Testing Patterns

## TDD Workflow (RED-GREEN-REFACTOR)

1. **RED**: Write a failing test first that describes desired behavior
2. **GREEN**: Write minimal code to make the test pass
3. **REFACTOR**: Clean up code while keeping tests green
4. **REPEAT**: Never write production code without a failing test

## Essential pytest-django Patterns

### Database Access
- Use `@pytest.mark.django_db` on any test touching the database
- Apply to entire module: `pytestmark = pytest.mark.django_db`
- Transactions roll back automatically after each test

### Fixtures for Test Data
**Use Factory Boy for models, pytest fixtures for setup:**
- **Factories**: Create model instances with realistic data (`UserFactory()`)
  - Use `factory.Sequence()` for unique fields
  - Use `factory.Faker()` for realistic fake data
  - Use `factory.SubFactory()` for foreign keys
- **Fixtures**: Setup clients, auth state, or shared resources

### Test Organization
```
tests/
├── apps/
│   └── <domain>/
│       ├── test_models.py
│       ├── test_views.py
│       └── test_forms.py
├── factories.py
└── conftest.py
```

## Setup Requirements

**In `pyproject.toml`:**
```toml
[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "config.settings"
python_files = ["test_*.py"]
addopts = ["--reuse-db", "-ra"]
```

## Running Tests
```bash
uv run pytest
uv run pytest -x
uv run pytest --lf
uv run pytest -k "test_name"
uv run pytest tests/apps/<domain>/
uv run pytest --cov=apps
```

## Common Pitfalls
- Forgetting `@pytest.mark.django_db` → "Database access not allowed"
- Not using factories → verbose and brittle test data
- Testing implementation details instead of behavior
- Over-mocking your own code
