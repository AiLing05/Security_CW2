from django.contrib import admin

from .models import SecurityEvent


@admin.register(SecurityEvent)
class SecurityEventAdmin(admin.ModelAdmin):
    """Read-only view of the audit trail inside Django admin."""

    list_display = ("timestamp", "event_type", "severity", "outcome", "actor_username", "ip_address", "path")
    list_filter = ("category", "severity", "outcome", "event_type")
    search_fields = ("actor_username", "ip_address", "path", "target_repr")
    date_hierarchy = "timestamp"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return bool(request.user.is_active and getattr(request.user, "role", "") == "admin")
