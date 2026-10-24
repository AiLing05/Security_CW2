"""
Rule-based suspicious-activity detection.

Each rule runs when a relevant event is logged, counts recent events in a
sliding time window and raises one alert per key per window (no alert floods).
Ashwin's login throttle *blocks* repeated attempts; these rules *detect and
record* them so an administrator can respond.
"""
from datetime import timedelta

from django.utils import timezone

from . import conf
from .models import EventType, Outcome, SecurityEvent, Severity


def evaluate(event):
    if event.event_type == EventType.LOGIN_FAILED:
        _failed_login_per_user(event)
        _failed_login_per_ip(event)
    elif event.event_type in (EventType.ACCESS_DENIED, EventType.TOKEN_REFRESH_FAILED):
        _access_probing(event)
    elif event.event_type == EventType.ASSET_DELETED:
        _mass_deletion(event)


# ----------------------------------------------------------
# Helpers
# ----------------------------------------------------------
def _since(minutes):
    return timezone.now() - timedelta(minutes=minutes)


def _already_alerted(alert_type, key, since):
    return SecurityEvent.objects.filter(
        event_type=alert_type, timestamp__gte=since, details__key=key
    ).exists()


def _raise_alert(alert_type, source_event, severity, key, reason, **extra):
    from .services import log_event

    log_event(
        alert_type,
        request=None,
        actor_username=source_event.actor_username,
        severity=severity,
        outcome=Outcome.FAILURE,
        target_type="SecurityEvent",
        target_id=str(source_event.pk),
        target_repr=reason,
        details={"key": key, "reason": reason, "source_ip": source_event.ip_address, **extra},
        run_detection=False,
    )


# ----------------------------------------------------------
# Rules
# ----------------------------------------------------------
def _failed_login_per_user(event):
    if not event.actor_username:
        return
    window = conf.detection("FAILED_LOGIN_WINDOW_MINUTES")
    since = _since(window)
    count = SecurityEvent.objects.filter(
        event_type=EventType.LOGIN_FAILED, actor_username=event.actor_username, timestamp__gte=since
    ).count()
    key = f"user:{event.actor_username}"
    if count >= conf.detection("FAILED_LOGIN_PER_USER") and not _already_alerted(
        EventType.BRUTE_FORCE_SUSPECTED, key, since
    ):
        _raise_alert(
            EventType.BRUTE_FORCE_SUSPECTED, event, Severity.HIGH, key,
            f"{count} failed logins for '{event.actor_username}' in {window} min",
            failed_attempts=count, window_minutes=window,
        )


def _failed_login_per_ip(event):
    if not event.ip_address:
        return
    window = conf.detection("FAILED_LOGIN_WINDOW_MINUTES")
    since = _since(window)
    recent = SecurityEvent.objects.filter(
        event_type=EventType.LOGIN_FAILED, ip_address=event.ip_address, timestamp__gte=since
    )
    count = recent.count()
    usernames = recent.values("actor_username").distinct().count()
    key = f"ip:{event.ip_address}"
    if (
        count >= conf.detection("FAILED_LOGIN_PER_IP")
        or usernames >= conf.detection("DISTINCT_USERNAMES_PER_IP")
    ) and not _already_alerted(EventType.CREDENTIAL_STUFFING_SUSPECTED, key, since):
        _raise_alert(
            EventType.CREDENTIAL_STUFFING_SUSPECTED, event, Severity.HIGH, key,
            f"{count} failed logins against {usernames} account(s) from {event.ip_address} in {window} min",
            failed_attempts=count, distinct_usernames=usernames, window_minutes=window,
        )


def _access_probing(event):
    window = conf.detection("ACCESS_DENIED_WINDOW_MINUTES")
    since = _since(window)
    qs = SecurityEvent.objects.filter(
        event_type__in=[EventType.ACCESS_DENIED, EventType.TOKEN_REFRESH_FAILED], timestamp__gte=since
    )
    if event.actor_id:
        qs, key = qs.filter(actor_id=event.actor_id), f"user:{event.actor_username}"
    elif event.ip_address:
        qs, key = qs.filter(ip_address=event.ip_address), f"ip:{event.ip_address}"
    else:
        return
    count = qs.count()
    if count >= conf.detection("ACCESS_DENIED_THRESHOLD") and not _already_alerted(
        EventType.ACCESS_PROBING_SUSPECTED, key, since
    ):
        _raise_alert(
            EventType.ACCESS_PROBING_SUSPECTED, event, Severity.WARNING, key,
            f"{count} denied requests from {key} in {window} min",
            denied_requests=count, window_minutes=window,
        )


def _mass_deletion(event):
    if not event.actor_id:
        return
    window = conf.detection("MASS_DELETE_WINDOW_MINUTES")
    since = _since(window)
    count = SecurityEvent.objects.filter(
        event_type=EventType.ASSET_DELETED, actor_id=event.actor_id, timestamp__gte=since
    ).count()
    key = f"user:{event.actor_username}"
    if count >= conf.detection("MASS_DELETE_THRESHOLD") and not _already_alerted(
        EventType.MASS_DELETION_SUSPECTED, key, since
    ):
        _raise_alert(
            EventType.MASS_DELETION_SUSPECTED, event, Severity.CRITICAL, key,
            f"{count} assets deleted by '{event.actor_username}' in {window} min",
            deleted_assets=count, window_minutes=window,
        )
