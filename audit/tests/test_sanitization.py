"""Secrets never reach the audit trail; log forging is neutralised."""
from pathlib import Path

from django.conf import settings

from audit.models import SecurityEvent
from audit.sanitize import REDACTED, clean_text, sanitize
from audit.services import log_event

from .helpers import AuditTestCase


class SanitizeUnitTests(AuditTestCase):
    def test_sensitive_keys_are_redacted(self):
        cleaned = sanitize({
            "password": "hunter2", "refresh": "abc", "Authorization": "Bearer x",
            "nested": {"api_key": "k", "title": "ok"},
        })
        self.assertEqual(cleaned["password"], REDACTED)
        self.assertEqual(cleaned["refresh"], REDACTED)
        self.assertEqual(cleaned["Authorization"], REDACTED)
        self.assertEqual(cleaned["nested"]["api_key"], REDACTED)
        self.assertEqual(cleaned["nested"]["title"], "ok")

    def test_jwt_inside_free_text_is_redacted(self):
        text = "token=eyJhbGciOiJIUzI1NiJ9.eyJ1c2VyIjoxfQ.c2lnbmF0dXJl end"
        self.assertNotIn("eyJ", clean_text(text))

    def test_crlf_log_injection_is_neutralised(self):
        forged = "bob\r\n2026-10-24 LOGIN_SUCCESS admin"
        event = log_event("LOGIN_FAILED", actor_username=forged, run_detection=False)
        self.assertNotIn("\n", event.actor_username)
        self.assertNotIn("\r", event.actor_username)

    def test_long_values_are_truncated(self):
        self.assertLessEqual(len(clean_text("A" * 10_000)), 256)


class NoSecretsEndToEndTests(AuditTestCase):
    def test_failed_login_never_stores_the_password(self):
        secret = "Wr0ng-But-Secret-Passw0rd"
        self.login("viewer1", password=secret)
        for event in SecurityEvent.objects.all():
            self.assertNotIn(secret, event.canonical())

    def test_access_and_refresh_tokens_never_stored(self):
        tokens = self.auth_as(self.viewer)
        self.client.get("/api/audit/summary/")  # 403 -> ACCESS_DENIED with Bearer header
        self.client.post("/api/token/refresh/", {"refresh": "not-a-real-token"}, format="json")
        records = "".join(e.canonical() for e in SecurityEvent.objects.all())
        self.assertNotIn(tokens["access"], records)
        self.assertNotIn(tokens["refresh"], records)

    def test_file_log_contains_no_password(self):
        secret = "Another-Secret-Passw0rd"
        self.login("viewer1", password=secret)
        log_file = Path(settings.LOG_DIR) / "security.log"
        self.assertTrue(log_file.exists())
        self.assertNotIn(secret, log_file.read_text(encoding="utf-8"))
