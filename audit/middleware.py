"""
AuditMiddleware

1. Makes the current request available to signal receivers (who/where).
2. After the view has run, records events that are only visible from the
   HTTP response: successful logins, logouts, 401/403 denials, 429 rate
   limiting, failed token refresh, asset views and file downloads.

It never changes the request or response.
"""
import json

from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import NoReverseMatch, reverse

from .context import reset_current_request, set_current_request
from .models import EventType, Outcome, Severity
from .services import log_event


def _safe_reverse(name):
    try:
        return reverse(name)
    except NoReverseMatch:
        return None


class AuditMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        login_username = self._login_username_from_body(request)
        token = set_current_request(request)
        try:
            response = self.get_response(request)
            self._audit_response(request, response, login_username)
            return response
        finally:
            reset_current_request(token)

    # -------------------- helpers --------------------
    @staticmethod
    def _login_username_from_body(request):
        """Read only the username (never the password) from a login POST."""
        if request.method != "POST" or request.path != _safe_reverse("token_obtain_pair"):
            return None
        try:
            if request.content_type == "application/json":
                return str(json.loads(request.body or b"{}").get("username", ""))[:150]
            return str(request.POST.get("username", ""))[:150]
        except (ValueError, AttributeError):
            return None

    @staticmethod
    def _url_name(request):
        match = getattr(request, "resolver_match", None)
        return match.url_name if match else None

    def _audit_response(self, request, response, login_username):
        status = response.status_code
        url_name = self._url_name(request)
        is_api = request.path.startswith("/api/")
        media_url = getattr(settings, "MEDIA_URL", "/media/") or "/media/"

        # -------------------- Authentication --------------------
        if url_name == "token_obtain_pair":
            if status == 200:
                data = getattr(response, "data", None) or {}
                username = data.get("username") or login_username or ""
                user = get_user_model().objects.filter(username=username).first()
                log_event(
                    EventType.LOGIN_SUCCESS, request=request, actor=user,
                    actor_username=username, status_code=status,
                )
            elif status == 429:
                log_event(
                    EventType.RATE_LIMITED, request=request, actor_username=login_username,
                    severity=Severity.WARNING, outcome=Outcome.DENIED, status_code=status,
                    details={"endpoint": "login"},
                )
            # 401 on login is recorded by the user_login_failed signal
            return

        if url_name == "token_refresh" and status in (400, 401):
            log_event(
                EventType.TOKEN_REFRESH_FAILED, request=request, severity=Severity.WARNING,
                outcome=Outcome.FAILURE, status_code=status,
                details={"reason": "invalid, expired or revoked refresh token"},
            )
            return

        if url_name == "logout" and status in (200, 204, 205):
            log_event(EventType.LOGOUT, request=request, status_code=status)
            return

        # -------------------- Access control --------------------
        if is_api and status in (401, 403):
            log_event(
                EventType.ACCESS_DENIED, request=request,
                severity=Severity.WARNING, outcome=Outcome.DENIED, status_code=status,
                details={"reason": "unauthenticated" if status == 401 else "forbidden"},
            )
            return

        if is_api and status == 429:
            log_event(
                EventType.RATE_LIMITED, request=request, severity=Severity.WARNING,
                outcome=Outcome.DENIED, status_code=status,
            )
            return

        # -------------------- Asset access --------------------
        if request.method == "GET" and status == 200:
            if url_name == "assets-detail":
                pk = request.resolver_match.kwargs.get("pk", "")
                log_event(
                    EventType.ASSET_VIEWED, request=request, status_code=status,
                    target_type="Asset", target_id=str(pk),
                )
            elif request.path.startswith(media_url):
                log_event(
                    EventType.ASSET_DOWNLOADED, request=request, status_code=status,
                    target_type="File", target_repr=request.path[len(media_url):],
                )
