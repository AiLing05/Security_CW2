"""
Signal receivers that record security events without editing assets/views.py.

The acting user and IP come from audit.context (set by AuditMiddleware).
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_login_failed
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from assets.models import Asset, AssetVersion, Category, Tag

from .models import EventType, Outcome, Severity
from .services import log_event

User = get_user_model()

# Fields compared before/after save. Password is compared but never stored.
TRACKED_FIELDS = {
    User: ["username", "email", "first_name", "last_name", "role", "is_staff", "is_superuser", "is_active", "password"],
    Asset: ["title", "description", "category_id", "version", "file", "metadata"],
    AssetVersion: ["status"],
    Category: ["name"],
    Tag: ["name"],
}


def _snapshot(instance, fields):
    return {f: (str(getattr(instance, f)) if f == "file" else getattr(instance, f)) for f in fields}


@receiver(pre_save)
def remember_previous_values(sender, instance, raw=False, **kwargs):
    fields = TRACKED_FIELDS.get(sender)
    if raw or not fields or instance.pk is None:
        return
    previous = sender.objects.filter(pk=instance.pk).first()
    instance._audit_previous = _snapshot(previous, fields) if previous else None


def _changes(sender, instance):
    previous = getattr(instance, "_audit_previous", None)
    if previous is None:
        return {}
    current = _snapshot(instance, TRACKED_FIELDS[sender])
    return {f: (previous[f], current[f]) for f in current if previous[f] != current[f]}


# ----------------------------------------------------------
# Authentication
# ----------------------------------------------------------
@receiver(user_login_failed)
def on_login_failed(sender, credentials, request=None, **kwargs):
    # Django already masks the password in `credentials`; we keep only the username.
    username = str(credentials.get("username", ""))[:150]
    known = User.objects.filter(username=username).exists()
    log_event(
        EventType.LOGIN_FAILED,
        request=getattr(request, "_request", request),
        actor_username=username,
        severity=Severity.WARNING,
        outcome=Outcome.FAILURE,
        status_code=401,
        # Stored for investigation only; the API response stays generic.
        details={"account_exists": known},
    )


# ----------------------------------------------------------
# Users and roles
# ----------------------------------------------------------
@receiver(post_save, sender=User)
def on_user_saved(sender, instance, created, raw=False, update_fields=None, **kwargs):
    if raw:
        return
    if update_fields is not None and set(update_fields) <= {"last_login"}:
        return  # routine login bookkeeping
    if created:
        log_event(
            EventType.USER_CREATED, target=instance,
            details={"role": instance.role, "is_staff": instance.is_staff, "is_superuser": instance.is_superuser},
        )
        return

    changes = _changes(sender, instance)
    if "role" in changes:
        old, new = changes.pop("role")
        log_event(
            EventType.ROLE_CHANGED, target=instance,
            severity=Severity.HIGH if new == "admin" else Severity.WARNING,
            details={"from": old, "to": new},
        )
    privilege = {f: changes.pop(f) for f in ("is_staff", "is_superuser") if f in changes}
    if privilege:
        escalated = any(new for _, new in privilege.values())
        log_event(
            EventType.PRIVILEGE_CHANGED, target=instance,
            severity=Severity.HIGH if escalated else Severity.WARNING,
            details={f: {"from": o, "to": n} for f, (o, n) in privilege.items()},
        )
    if "is_active" in changes:
        old, new = changes.pop("is_active")
        log_event(
            EventType.ACCOUNT_STATUS_CHANGED, target=instance, severity=Severity.WARNING,
            details={"active": new},
        )
    if changes.pop("password", None):
        log_event(EventType.PASSWORD_CHANGED, target=instance)
    if changes:
        log_event(EventType.USER_UPDATED, target=instance, details={"fields": sorted(changes)})


@receiver(post_delete, sender=User)
def on_user_deleted(sender, instance, **kwargs):
    log_event(
        EventType.USER_DELETED, target=instance, severity=Severity.WARNING,
        details={"role": instance.role},
    )


# ----------------------------------------------------------
# Assets and versions
# ----------------------------------------------------------
def _file_info(field_file):
    info = {"file": str(field_file) if field_file else ""}
    try:
        info["size_bytes"] = field_file.size
    except Exception:
        pass
    return info


@receiver(post_save, sender=Asset)
def on_asset_saved(sender, instance, created, raw=False, **kwargs):
    if raw:
        return
    if created:
        log_event(
            EventType.ASSET_UPLOADED, target=instance,
            details={**_file_info(instance.file), "category_id": instance.category_id},
        )
        return
    changes = _changes(sender, instance)
    if changes:
        log_event(EventType.ASSET_UPDATED, target=instance, details={"fields": sorted(changes)})


@receiver(post_delete, sender=Asset)
def on_asset_deleted(sender, instance, **kwargs):
    log_event(
        EventType.ASSET_DELETED, target=instance, severity=Severity.WARNING,
        details={"file": str(instance.file), "owner_id": instance.uploaded_by_id},
    )


@receiver(post_save, sender=AssetVersion)
def on_version_saved(sender, instance, created, raw=False, **kwargs):
    if raw:
        return
    target = {"target_type": "AssetVersion", "target_id": str(instance.pk),
              "target_repr": f"asset {instance.asset_id} v{instance.version}"}
    if created:
        if instance.status == "pending":
            log_event(
                EventType.VERSION_SUBMITTED, **target,
                details={**_file_info(instance.file), "asset_id": instance.asset_id},
            )
        return
    changes = _changes(sender, instance)
    if "status" in changes:
        old, new = changes["status"]
        event = {"approved": EventType.VERSION_APPROVED, "rejected": EventType.VERSION_REJECTED}.get(new)
        if event:
            log_event(event, **target, details={"from": old, "to": new, "asset_id": instance.asset_id})


@receiver(post_delete, sender=AssetVersion)
def on_version_deleted(sender, instance, **kwargs):
    log_event(
        EventType.VERSION_DELETED, severity=Severity.WARNING,
        target_type="AssetVersion", target_id=str(instance.pk),
        target_repr=f"asset {instance.asset_id} v{instance.version}",
    )


# ----------------------------------------------------------
# Categories and tags (administrative data)
# ----------------------------------------------------------
ADMIN_EVENTS = {
    Category: (EventType.CATEGORY_CREATED, EventType.CATEGORY_UPDATED, EventType.CATEGORY_DELETED),
    Tag: (EventType.TAG_CREATED, EventType.TAG_UPDATED, EventType.TAG_DELETED),
}


@receiver(post_save, sender=Category)
@receiver(post_save, sender=Tag)
def on_admin_object_saved(sender, instance, created, raw=False, **kwargs):
    if raw:
        return
    created_event, updated_event, _ = ADMIN_EVENTS[sender]
    if created:
        log_event(created_event, target=instance)
    else:
        changes = _changes(sender, instance)
        if changes:
            log_event(updated_event, target=instance, details={"from": changes["name"][0], "to": changes["name"][1]})


@receiver(post_delete, sender=Category)
@receiver(post_delete, sender=Tag)
def on_admin_object_deleted(sender, instance, **kwargs):
    log_event(ADMIN_EVENTS[sender][2], target=instance, severity=Severity.WARNING)
