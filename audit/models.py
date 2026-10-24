import hashlib
import json

from django.db import models


class AuditLogImmutableError(Exception):
    """Raised when code tries to change or remove an audit record."""


# ----------------------------------------------------------
# Event catalogue
# ----------------------------------------------------------
class EventType(models.TextChoices):
    # Authentication
    LOGIN_SUCCESS = "LOGIN_SUCCESS", "Login success"
    LOGIN_FAILED = "LOGIN_FAILED", "Login failed"
    LOGOUT = "LOGOUT", "Logout"
    TOKEN_REFRESH_FAILED = "TOKEN_REFRESH_FAILED", "Token refresh failed"
    RATE_LIMITED = "RATE_LIMITED", "Request rate limited"
    # Authorization
    ACCESS_DENIED = "ACCESS_DENIED", "Access denied"
    # Assets
    ASSET_UPLOADED = "ASSET_UPLOADED", "Asset uploaded"
    ASSET_UPDATED = "ASSET_UPDATED", "Asset updated"
    ASSET_DELETED = "ASSET_DELETED", "Asset deleted"
    ASSET_VIEWED = "ASSET_VIEWED", "Asset viewed"
    ASSET_DOWNLOADED = "ASSET_DOWNLOADED", "Asset file downloaded"
    VERSION_SUBMITTED = "VERSION_SUBMITTED", "Version submitted"
    VERSION_APPROVED = "VERSION_APPROVED", "Version approved"
    VERSION_REJECTED = "VERSION_REJECTED", "Version rejected"
    VERSION_DELETED = "VERSION_DELETED", "Version deleted"
    # Administration
    CATEGORY_CREATED = "CATEGORY_CREATED", "Category created"
    CATEGORY_UPDATED = "CATEGORY_UPDATED", "Category updated"
    CATEGORY_DELETED = "CATEGORY_DELETED", "Category deleted"
    TAG_CREATED = "TAG_CREATED", "Tag created"
    TAG_UPDATED = "TAG_UPDATED", "Tag updated"
    TAG_DELETED = "TAG_DELETED", "Tag deleted"
    USER_CREATED = "USER_CREATED", "User created"
    USER_UPDATED = "USER_UPDATED", "User updated"
    USER_DELETED = "USER_DELETED", "User deleted"
    ROLE_CHANGED = "ROLE_CHANGED", "Role changed"
    PRIVILEGE_CHANGED = "PRIVILEGE_CHANGED", "Staff/superuser flag changed"
    ACCOUNT_STATUS_CHANGED = "ACCOUNT_STATUS_CHANGED", "Account enabled/disabled"
    PASSWORD_CHANGED = "PASSWORD_CHANGED", "Password changed"
    # Audit trail itself
    AUDIT_LOG_VIEWED = "AUDIT_LOG_VIEWED", "Audit log viewed"
    AUDIT_LOG_PURGED = "AUDIT_LOG_PURGED", "Audit log retention purge"
    # Detection alerts
    BRUTE_FORCE_SUSPECTED = "BRUTE_FORCE_SUSPECTED", "Brute force suspected"
    CREDENTIAL_STUFFING_SUSPECTED = "CREDENTIAL_STUFFING_SUSPECTED", "Credential stuffing suspected"
    ACCESS_PROBING_SUSPECTED = "ACCESS_PROBING_SUSPECTED", "Access-control probing suspected"
    MASS_DELETION_SUSPECTED = "MASS_DELETION_SUSPECTED", "Mass deletion suspected"


class Category(models.TextChoices):
    AUTHENTICATION = "authentication", "Authentication"
    AUTHORIZATION = "authorization", "Authorization"
    ASSET = "asset", "Asset"
    ADMIN = "admin", "Administration"
    AUDIT = "audit", "Audit"
    DETECTION = "detection", "Detection"


class Severity(models.TextChoices):
    INFO = "info", "Info"
    WARNING = "warning", "Warning"
    HIGH = "high", "High"
    CRITICAL = "critical", "Critical"


class Outcome(models.TextChoices):
    SUCCESS = "success", "Success"
    FAILURE = "failure", "Failure"
    DENIED = "denied", "Denied"


# ----------------------------------------------------------
# Append-only QuerySet / Manager
# ----------------------------------------------------------
class SecurityEventQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise AuditLogImmutableError("Audit records cannot be updated.")

    def delete(self):
        raise AuditLogImmutableError("Audit records cannot be deleted.")

    def _retention_purge(self):
        """Only used by the purge_audit_logs command (retention policy)."""
        return super().delete()


# ----------------------------------------------------------
# Security event (audit record)
# ----------------------------------------------------------
class SecurityEvent(models.Model):
    timestamp = models.DateTimeField(db_index=True)
    event_type = models.CharField(max_length=40, choices=EventType.choices, db_index=True)
    category = models.CharField(max_length=20, choices=Category.choices, db_index=True)
    severity = models.CharField(max_length=10, choices=Severity.choices, default=Severity.INFO, db_index=True)
    outcome = models.CharField(max_length=10, choices=Outcome.choices, default=Outcome.SUCCESS)

    # Snapshot of who did it. Deliberately not a ForeignKey so the record
    # survives user deletion unchanged (assets cascade-delete with users).
    actor_id = models.BigIntegerField(null=True, blank=True, db_index=True)
    actor_username = models.CharField(max_length=150, blank=True, db_index=True)
    actor_role = models.CharField(max_length=20, blank=True)

    ip_address = models.GenericIPAddressField(null=True, blank=True, db_index=True)
    user_agent = models.CharField(max_length=256, blank=True)
    method = models.CharField(max_length=10, blank=True)
    path = models.CharField(max_length=256, blank=True)
    status_code = models.PositiveSmallIntegerField(null=True, blank=True)

    target_type = models.CharField(max_length=50, blank=True)
    target_id = models.CharField(max_length=64, blank=True)
    target_repr = models.CharField(max_length=256, blank=True)

    details = models.JSONField(default=dict, blank=True)

    # Tamper evidence: hash = SHA256(prev_hash + canonical record)
    prev_hash = models.CharField(max_length=64, blank=True)
    hash = models.CharField(max_length=64, unique=True)

    objects = SecurityEventQuerySet.as_manager()

    class Meta:
        ordering = ["-timestamp", "-id"]
        indexes = [
            models.Index(fields=["event_type", "timestamp"]),
            models.Index(fields=["ip_address", "event_type", "timestamp"]),
        ]

    def __str__(self):
        return f"{self.timestamp:%Y-%m-%d %H:%M:%S} {self.event_type} {self.actor_username or '-'}"

    # -------------------- Hash chain --------------------
    def canonical(self):
        """Stable JSON of every recorded field (excluding id and hash)."""
        return json.dumps(
            {
                "timestamp": self.timestamp.isoformat(),
                "event_type": self.event_type,
                "category": self.category,
                "severity": self.severity,
                "outcome": self.outcome,
                "actor_id": self.actor_id,
                "actor_username": self.actor_username,
                "actor_role": self.actor_role,
                "ip_address": self.ip_address,
                "user_agent": self.user_agent,
                "method": self.method,
                "path": self.path,
                "status_code": self.status_code,
                "target_type": self.target_type,
                "target_id": self.target_id,
                "target_repr": self.target_repr,
                "details": self.details,
                "prev_hash": self.prev_hash,
            },
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )

    def compute_hash(self):
        return hashlib.sha256(self.canonical().encode("utf-8")).hexdigest()

    # -------------------- Append-only --------------------
    def save(self, *args, **kwargs):
        if self.pk is not None or not self._state.adding:
            raise AuditLogImmutableError("Audit records cannot be modified.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise AuditLogImmutableError("Audit records cannot be deleted.")
