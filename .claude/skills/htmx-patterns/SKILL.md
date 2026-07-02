---
name: htmx-patterns
description: HTMX patterns for Django including partial templates, hx-* attributes, and dynamic UI without JavaScript. Use when building interactive UI, handling AJAX requests, or creating dynamic components.
---

# HTMX Patterns for Django

## Core Philosophy
- Server renders HTML, not JSON
- Partial templates for dynamic updates (`_partial.html` files)
- Progressive enhancement — pages work without JavaScript

## Critical Rules

**Always detect HTMX requests:**
```python
if request.headers.get("HX-Request"):
    return render(request, "app/_partial.html", context)
return render(request, "app/full_page.html", context)
```

**Always return partials for HTMX** — full page responses break UX.

**Template naming:**
- Partials: `_partial.html` (underscore prefix)
- Full pages: `page.html`

## Form Handling Pattern
```python
def create_view(request):
    if request.method == "POST":
        form = MyForm(request.POST)
        if form.is_valid():
            obj = form.save()
            if request.headers.get("HX-Request"):
                return render(request, "app/_item.html", {"item": obj})
            return redirect("app:list")
        if request.headers.get("HX-Request"):
            return render(request, "app/_form.html", {"form": form})
    else:
        form = MyForm()
    return render(request, "app/create.html", {"form": form})
```

## Response Headers
- `HX-Trigger` — trigger client-side events after response
- `HX-Redirect` — client-side redirect
- `HX-Retarget` / `HX-Reswap` — override target from server
- `HX-Refresh` — force full page refresh

## Common Pitfalls
- Missing `hx-indicator` loading states
- Returning full pages in HTMX responses
- Not handling form errors in partial
- Not disabling buttons with `hx-disabled-elt="this"`
- N+1 queries in HTMX views
