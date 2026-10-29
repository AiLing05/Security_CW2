"""
log_event() is the single entry point for writing to the audit trail.

Other modules can call it directly, for example:
    from audit.services import log_event
    log_event("ASSET_DOWNLOADED", target=asset)
but most events are captured automatically by audit.middleware and audit.signals.
"""
import ipaddress
import json
import logging

from django.db import connection, transaction
from django.utils import timezone

from . import conf
from .context import get_current_request
from .models import EventType, SecurityEvent, Severity, Outcome
from .sanitize import clean_text, sanitize

security_logger = logging.getLogger("dam.security")

# Arbitrary constant key for the PostgreSQL advisory lock that serialises
# hash-chain writes (prevents two events claiming the same prev_hash).
CHAIN_LOCK_KEY = 0x5EC_A0D1

CATEGORY_BY_PREFIX = {
    "LOGIN": "authentication",
    "LOGOUT": "authentication",
    "TOKEN": "authentication",  # nosec B105 - event-name prefix, not a secret
    "RATE": "authentication",
    "PASSWORD": "authentication",  # nosec B105 - event-name prefix, not a secret
    "ACCESS_DENIED": "authorization",
    "ASSET": "asset",
    "VERSION": "asset",
    "CATEGORY": "admin",
    "TAG": "admin",
    "USER": "admin",
    "ROLE": "admin",
    "PRIVILEGE": "admin",
    "ACCOUNT": "admin",
    "AUDIT": "audit",
}
DETECTION_EVENTS = {
    EventType.BRUTE_FORCE_SUSPECTED,
    EventType.CREDENTIAL_STUFFING_SUSPECTED,
    EventType.ACCESS_PROBING_SUSPECTED,
    EventType.MASS_DELETION_SUSPECTED,
}


def category_for(event_type):
    if event_type in DETECTION_EVENTS:
        return "detection"
    for prefix, category in CATEGORY_BY_PREFIX.items():
        if event_type.startswith(prefix):
            return category
    return "audit"


# ----------------------------------------------------------
# Request helpers
# ----------------------------------------------------------
def client_ip(request):
    """Client IP, trusting X-Forwarded-For only behind a configured proxy."""
    if request is None:
        return None
    candidate = request.META.get("REMOTE_ADDR")
    proxies = conf.trusted_proxy_count()
    if proxies > 0:
        chain = [p.strip() for p in request.META.get("HTTP_X_FORWARDED_FOR", "").split(",") if p.strip()]
        if len(chain) >= proxies:
            candidate = chain[-proxies]
    try:
        return str(ipaddress.ip_address(candidate))
    except (TypeError, ValueError):
        return None


def request_user(request):
    user = getattr(request, "user", None) if request is not None else None
    if user is not None and getattr(user, "is_authenticated", False):
        return user
    return None


# ----------------------------------------------------------
# Main API
# ----------------------------------------------------------
def log_event(
    event_type,
    *,
    request=None,
    actor=None,
    actor_username=None,
    severity=Severity.INFO,
    outcome=Outcome.SUCCESS,
    target=None,
    target_type="",
    target_id="",
    target_repr="",
    details=None,
    status_code=None,
    run_detection=True,
):
    """
    Write one append-only, hash-chained audit record.

    Never raises: a logging problem must not break the user's request,
    but it is reported to the server log.
    """
    try:
        request = request or get_current_request()
        actor = actor or request_user(request)

        if target is not None:
            target_type = target_type or target.__class__.__name__
            target_id = target_id or str(getattr(target, "pk", "") or "")
            target_repr = target_repr or str(target)

        event = SecurityEvent(
            timestamp=timezone.now(),
            event_type=str(event_type),
            category=category_for(str(event_type)),
            severity=str(severity),
            outcome=str(outcome),
            actor_id=getattr(actor, "pk", None),
            actor_username=clean_text(
                actor_username or getattr(actor, "username", "") or ("anonymous" if request else "system"), 150
            ),
            actor_role=clean_text(getattr(actor, "role", "") or "", 20),
            ip_address=client_ip(request),
            user_agent=clean_text(request.META.get("HTTP_USER_AGENT", "") if request else ""),
            method=(request.method if request else "")[:10],
            path=clean_text(request.path if request else ""),
            status_code=status_code,
            target_type=clean_text(target_type, 50),
            target_id=clean_text(target_id, 64),
            target_repr=clean_text(target_repr),
            details=sanitize(details or {}),
        )
        _append_to_chain(event)
        _write_file_log(event)
    except Exception:  # pragma: no cover - defensive
        security_logger.exception("Failed to write audit event %s", event_type)
        return None

    if run_detection:
        from .detection import evaluate

        try:
            evaluate(event)
        except Exception:  # pragma: no cover - defensive
            security_logger.exception("Detection failed for event %s", event.pk)
    return event


def _append_to_chain(event):
    with transaction.atomic():
        if connection.vendor == "postgresql":
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_xact_lock(%s)", [CHAIN_LOCK_KEY])
        last = SecurityEvent.objects.order_by("-id").values_list("hash", flat=True).first()
        event.prev_hash = last or ""
        event.hash = event.compute_hash()
        event.save()


def _write_file_log(event):
    """Second copy as one JSON line, for shipping to a SIEM / log collector."""
    security_logger.info(
        json.dumps(
            {
                "id": event.pk,
                "ts": event.timestamp.isoformat(),
                "event": event.event_type,
                "severity": event.severity,
                "outcome": event.outcome,
                "user": event.actor_username,
                "ip": event.ip_address,
                "path": event.path,
                "status": event.status_code,
                "target": f"{event.target_type}:{event.target_id}" if event.target_type else "",
                "hash": event.hash,
            },
            default=str,
        )
    )


def verify_chain():
    """
    Recompute every hash in insertion order.
    Returns (ok, checked_count, first_bad_event_id).
    """
    previous = None
    checked = 0
    for event in SecurityEvent.objects.order_by("id").iterator():
        # The oldest remaining record after a retention purge anchors the chain.
        if previous is not None and event.prev_hash != previous:
            return False, checked, event.pk
        if event.compute_hash() != event.hash:
            return False, checked, event.pk
        previous = event.hash
        checked += 1
    return True, checked, None
