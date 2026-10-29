from django.apps import AppConfig


class AuditConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "audit"
    verbose_name = "Security Audit"

    def ready(self):
        # Register signal receivers (login failures, model changes, role changes)
        from . import signals  # noqa: F401
