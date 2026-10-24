"""
Audit settings with safe defaults.

Any value can be overridden in dam_backend/settings.py, e.g.
    AUDIT_LOG_RETENTION_DAYS = 180
"""
from django.conf import settings

DEFAULT_DETECTION = {
    # Brute force against one account
    "FAILED_LOGIN_PER_USER": 5,
    "FAILED_LOGIN_WINDOW_MINUTES": 10,
    # Brute force / credential stuffing from one IP
    "FAILED_LOGIN_PER_IP": 10,
    "DISTINCT_USERNAMES_PER_IP": 5,
    # Repeated 401/403 responses (access-control probing)
    "ACCESS_DENIED_THRESHOLD": 10,
    "ACCESS_DENIED_WINDOW_MINUTES": 5,
    # Many deletions in a short time
    "MASS_DELETE_THRESHOLD": 5,
    "MASS_DELETE_WINDOW_MINUTES": 5,
}


def retention_days():
    return int(getattr(settings, "AUDIT_LOG_RETENTION_DAYS", 365))


def trusted_proxy_count():
    # 0 = trust only REMOTE_ADDR. Only raise this when a reverse proxy we
    # control sets X-Forwarded-For, otherwise attackers can spoof their IP.
    return int(getattr(settings, "AUDIT_TRUSTED_PROXY_COUNT", 0))


def detection(key):
    overrides = getattr(settings, "AUDIT_DETECTION", {})
    return overrides.get(key, DEFAULT_DETECTION[key])
