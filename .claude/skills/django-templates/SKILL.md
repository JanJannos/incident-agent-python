---
name: django-templates
description: Django template patterns including inheritance, partials, tags, and filters. Use when working with templates, creating reusable components, or organizing template structure.
---

# Django Template Patterns

## Template Organization

```
templates/
├── base.html
├── partials/
├── components/
└── <domain>/
    ├── list.html
    ├── detail.html
    ├── _list.html      # HTMX partials (underscore prefix)
    └── _form.html
```

**Naming conventions:**
- Full pages: `list.html`, `detail.html`, `form.html`
- HTMX partials: `_list.html`, `_card.html` (underscore prefix)
- Shared partials: `partials/_navbar.html`
- Components: `components/_button.html`

## Template Inheritance

Three-level inheritance:
1. `base.html` — site-wide structure
2. Section templates — optional shared layouts
3. Page templates — individual pages

**Standard blocks in base.html:** `title`, `content`, `extra_css`, `extra_js`

## Custom Tags and Filters

- `simple_tag` — return a string value
- `inclusion_tag` — render a template fragment
- **Location:** `apps/<domain>/templatetags/<domain>_tags.py`

## Anti-Patterns
- Complex conditionals in templates (move to views/model methods)
- Hardcoded URLs (use `{% url 'name' %}`)
- Inline styles (use CSS classes)
- Loops without `{% empty %}` clause
