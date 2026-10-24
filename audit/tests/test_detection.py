"""Suspicious-activity rules raise exactly one alert when thresholds are met."""
from assets.models import Asset

from .helpers import AuditTestCase


class BruteForceDetectionTests(AuditTestCase):
    def test_four_failures_do_not_alert(self):
        for _ in range(4):
            self.login("editor1", password="wrong")
        self.assertFalse(self.events("BRUTE_FORCE_SUSPECTED").exists())

    def test_five_failures_raise_one_high_severity_alert(self):
        for _ in range(8):
            self.login("editor1", password="wrong")
        alerts = self.events("BRUTE_FORCE_SUSPECTED")
        self.assertEqual(alerts.count(), 1)  # de-duplicated within the window
        alert = alerts.get()
        self.assertEqual(alert.severity, "high")
        self.assertEqual(alert.category, "detection")
        self.assertEqual(alert.details["key"], "user:editor1")
        self.assertEqual(alert.details["failed_attempts"], 5)

    def test_credential_stuffing_across_many_accounts_from_one_ip(self):
        for name in ["alice", "bob", "carol", "dave", "erin"]:
            self.login(name, password="Summer2026!", ip="192.0.2.99")
        alert = self.events("CREDENTIAL_STUFFING_SUSPECTED").get()
        self.assertEqual(alert.details["key"], "ip:192.0.2.99")
        self.assertEqual(alert.details["distinct_usernames"], 5)

    def test_failures_from_different_ips_tracked_separately(self):
        for i in range(4):
            self.login(f"user{i}", password="x", ip="192.0.2.1")
            self.login(f"user{i}", password="x", ip="192.0.2.2")
        self.assertFalse(self.events("CREDENTIAL_STUFFING_SUSPECTED").exists())


class AccessProbingDetectionTests(AuditTestCase):
    def test_repeated_forbidden_requests_raise_alert(self):
        self.auth_as(self.viewer)
        for i in range(10):
            self.client.delete(f"/api/categories/{i}/")
        alert = self.events("ACCESS_PROBING_SUSPECTED").get()
        self.assertEqual(alert.details["key"], "user:viewer1")


class MassDeletionDetectionTests(AuditTestCase):
    def test_bulk_asset_deletion_raises_critical_alert(self):
        self.auth_as(self.admin)
        ids = []
        for i in range(5):
            response = self.client.post(
                "/api/assets/", {"title": f"a{i}", "file": self.png(f"a{i}.png")}, format="multipart"
            )
            ids.append(response.data["id"])
        for pk in ids:
            self.client.delete(f"/api/assets/{pk}/")
        self.assertEqual(Asset.objects.count(), 0)
        alert = self.events("MASS_DELETION_SUSPECTED").get()
        self.assertEqual(alert.severity, "critical")
