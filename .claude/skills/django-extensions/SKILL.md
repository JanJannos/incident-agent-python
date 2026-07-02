---
name: django-extensions
description: Django-extensions management commands for project introspection, debugging, and development. Use when exploring URLs, models, settings, database schema, running scripts, or profiling performance. Triggers on questions about Django project structure, model fields, URL routes, or requests to run development servers.
---

# Django Extensions

This project has django-extensions installed. Use these commands to understand and interact with the Django project.

### Introspection Commands
- `python manage.py show_urls` - Display URL routes
- `python manage.py list_model_info` - Show model details
- `python manage.py print_settings` - View settings with wildcard support
- `python manage.py show_permissions` - List available permissions
- `python manage.py show_template_tags` - Display template tags

### Development Commands
- `python manage.py shell_plus` - Auto-imports all models
- `python manage.py runserver_plus` - Includes Werkzeug debugger

### Database Commands
- `python manage.py sqldiff` - Compare models to database schema

### Script Execution
- `python manage.py runscript <script_name>` - Execute scripts with Django context

### Profiling Commands
- `python manage.py runprofileserver` - Profile server requests

**Key Notes:**
- Model notation uses `app.ModelName` format
- Commands execute from project root
- Scripts require a `run()` function defined
