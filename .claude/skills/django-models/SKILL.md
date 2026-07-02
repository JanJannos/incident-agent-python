---
name: django-models
description: Django model design patterns emphasizing fat models/thin views, QuerySet optimization, and domain logic encapsulation. Use when designing models, optimizing queries, implementing business logic, or working with the ORM.
---

# Django Model Patterns

## Core Philosophy: Fat Models, Thin Views

Business logic belongs in models and managers, not views. Views orchestrate; models implement domain behavior.

## Model Design

- Use `TextChoices`/`IntegerChoices` for status fields
- Add `get_absolute_url()` for canonical URLs
- Include `__str__()` for readable representations
- Set `ordering` in Meta for consistent default sorting
- Add database indexes for frequently filtered/sorted fields
- Use abstract base models for shared fields (timestamps, soft deletes)

### Field Selection
- `blank=True, default=""` for optional text fields (avoid null on CharField)
- `null=True, blank=True` for optional foreign keys
- `JSONField` for flexible metadata
- Set appropriate `max_length` based on actual data

## QuerySet Patterns

Custom QuerySet classes make queries reusable and chainable:
```python
class PostQuerySet(models.QuerySet):
    def published(self):
        return self.filter(status=Post.Status.PUBLISHED)

    def recent(self):
        return self.order_by('-created_at')

class Post(models.Model):
    objects = PostQuerySet.as_manager()
```

## Query Optimization

1. `select_related()` for ForeignKey / OneToOneField (SQL JOIN)
2. `prefetch_related()` for ManyToMany / reverse FK (separate query)
3. `only()` for specific fields
4. `.exists()` instead of `if queryset:`
5. `.count()` instead of `len(queryset.all())`
6. `F()` for database-level updates

## Signals: Use Sparingly

Prefer explicit method calls over signals. Signals are acceptable for:
- Audit logging
- Cache invalidation
- Decoupling third-party apps

## Migrations

- Run `makemigrations` after model changes
- Review generated files before applying
- Use `makemigrations --empty <app>` for data migrations
- Write both forward and reverse operations

## Anti-Patterns
- Business logic in views
- Iterating over relations without `select_related()`/`prefetch_related()`
- Using `if queryset:` instead of `.exists()`
- Forgetting indexes on filtered/sorted fields
