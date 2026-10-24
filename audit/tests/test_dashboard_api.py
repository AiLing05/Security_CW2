"""Audit data is only visible to admins (RBAC / least privilege) and is read-only."""
from datetime import timedelta

from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

from audit.models import SecurityEvent
from audit.services import _append_to_chain, verify_chain

from .helpers import AuditTestCase

ENDPOINTS = ["/api/audit/events/", "/api/audit/summary/", "/api/audit/integrity/"]


class DashboardAccessControlTests(AuditTestCase):
    def test_anonymous_gets_401(self):
        for url in ENDPOINTS:
            self.assertEqual(self.client.get(url).status_code, 401, url)

    def test_viewer_and_editor_get_403(self):
        for user in (self.viewer, self.editor):
            self.auth_as(user)
            for url in ENDPOINTS:
                self.assertEqual(self.client.get(url).status_code, 403, f"{user.username} {url}")

    def test_admin_can_read_all_endpoints(self):
        self.auth_as(self.admin)
        for url in ENDPOINTS:
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_staff_flag_without_admin_role_is_not_enough(self):
        self.editor.is_staff = True
        self.editor.save()
        self.auth_as(self.editor)
        self.assertEqual(self.client.get("/api/audit/events/").status_code, 403)

    def test_no_write_operations_even_for_admin(self):
        self.auth_as(self.admin)
        event_id = SecurityEvent.objects.first().pk
        self.assertEqual(self.client.post("/api/audit/events/", {}).status_code, 403)
        self.assertEqual(self.client.put(f"/api/audit/events/{event_id}/", {}).status_code, 403)
        self.assertEqual(self.client.delete(f"/api/audit/events/{event_id}/").status_code, 403)
        self.assertTrue(SecurityEvent.objects.filter(pk=event_id).exists())

    def test_denied_dashboard_access_is_itself_logged(self):
        self.auth_as(self.viewer)
        self.client.get("/api/audit/events/")
        event = self.events("ACCESS_DENIED").get(path="/api/audit/events/")
        self.assertEqual(event.actor_username, "viewer1")

    def test_admin_viewing_audit_log_is_logged(self):
        self.auth_as(self.admin)
        self.client.get("/api/audit/events/?severity=high")
        viewed = self.events("AUDIT_LOG_VIEWED").get()
        self.assertEqual(viewed.actor_username, "admin1")
        self.assertEqual(viewed.details["filters"], {"severity": "high"})


class DashboardContentTests(AuditTestCase):
    def test_summary_counts_and_trend(self):
        for _ in range(5):
            self.login("editor1", password="wrong")
        self.auth_as(self.admin)
        data = self.client.get("/api/audit/summary/").data
        self.assertEqual(data["last_24h"]["login_failed"], 5)
        self.assertGreaterEqual(data["last_24h"]["login_success"], 1)
        self.assertEqual(data["last_24h"]["alerts"], 1)
        self.assertEqual(len(data["trend_7d"]), 7)
        self.assertEqual(data["trend_7d"][-1]["login_failed"], 5)
        self.assertEqual(data["top_failed_usernames_24h"][0], {"actor_username": "editor1", "count": 5})
        self.assertEqual(data["recent_alerts"][0]["event_type"], "BRUTE_FORCE_SUSPECTED")

    def test_event_list_filtering(self):
        self.login("editor1", password="wrong")
        self.auth_as(self.admin)
        data = self.client.get("/api/audit/events/?event_type=LOGIN_FAILED").data
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["actor_username"], "editor1")

    def test_integrity_endpoint_reports_intact_chain(self):
        self.auth_as(self.admin)
        data = self.client.get("/api/audit/integrity/").data
        self.assertTrue(data["intact"])
        self.assertGreater(data["records_checked"], 0)


class RetentionTests(AuditTestCase):
    def _old_event(self, days_ago):
        event = SecurityEvent(
            timestamp=timezone.now() - timedelta(days=days_ago), event_type="LOGIN_SUCCESS",
            category="authentication", actor_username="old-user",
        )
        _append_to_chain(event)
        return event

    def test_purge_removes_only_expired_records_and_logs_itself(self):
        SecurityEvent.objects.all()._retention_purge()  # start from an empty trail
        self._old_event(400)
        self._old_event(10)
        call_command("purge_audit_logs", "--days", "365")
        self.assertFalse(SecurityEvent.objects.filter(actor_username="old-user", timestamp__lt=timezone.now() - timedelta(days=365)).exists())
        self.assertTrue(SecurityEvent.objects.filter(actor_username="old-user").exists())
        purge = self.events("AUDIT_LOG_PURGED").get()
        self.assertEqual(purge.details["deleted"], 1)
        self.assertTrue(verify_chain()[0])  # remaining chain still verifies

    def test_dry_run_deletes_nothing(self):
        self._old_event(400)
        before = SecurityEvent.objects.count()
        call_command("purge_audit_logs", "--dry-run")
        self.assertEqual(SecurityEvent.objects.count(), before)

    def test_refuses_dangerously_short_retention(self):
        with self.assertRaises(CommandError):
            call_command("purge_audit_logs", "--days", "1")
