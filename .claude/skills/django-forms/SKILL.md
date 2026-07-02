---
name: django-forms
description: Django form handling patterns including ModelForm, validation, clean methods, and HTMX form submission. Use when building forms, implementing validation, or handling form submission.
---

# Django Forms

## Philosophy
- Prefer ModelForm for model-backed forms
- Keep validation logic in forms, not views
- Always handle and display form errors
- Use `commit=False` when you need to modify the instance before saving

## Validation

**Field-level** (`clean_<field>`):
- Validate and transform a single field
- Return cleaned value or raise `ValidationError`

**Cross-field** (`clean`):
- Call `super().clean()` first
- Access multiple fields via `cleaned_data`
- Use `self.add_error(field, message)` for field-specific errors

## View Integration
- Check `request.method` explicitly
- Instantiate form with `request.POST` for POST, empty for GET
- Use `form.save(commit=False)` to set additional fields
- Return redirect on success, re-render with form on error

**HTMX handling:**
- Check `request.headers.get("HX-Request")` for HTMX requests
- Return partial template on success/error for HTMX

## Pitfalls
- Validating in views instead of forms
- Redirecting without checking `is_valid()`
- Forgetting `commit=False` when setting related fields
- Not displaying form errors to users
