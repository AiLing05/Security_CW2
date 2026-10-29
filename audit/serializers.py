from rest_framework import serializers

from .models import SecurityEvent


class SecurityEventSerializer(serializers.ModelSerializer):
    event_label = serializers.CharField(source="get_event_type_display", read_only=True)

    class Meta:
        model = SecurityEvent
        fields = [
            "id", "timestamp", "event_type", "event_label", "category", "severity", "outcome",
            "actor_id", "actor_username", "actor_role", "ip_address", "user_agent",
            "method", "path", "status_code", "target_type", "target_id", "target_repr",
            "details", "hash",
        ]
        read_only_fields = fields
