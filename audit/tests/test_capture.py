"""Every security-relevant action produces an audit event (E1-E12)."""
from django.http import HttpResponse
from django.test import RequestFactory

from assets.models import Asset, AssetVersion, Category, Tag
from audit.middleware import AuditMiddleware
from audit.models import SecurityEvent

from .helpers import AuditTestCase


class AuthenticationEventTests(AuditTestCase):
    def test_successful_login_recorded_with_user_role_and_ip(self):
        self.login("editor1", ip="198.51.100.7")
        event = self.events("LOGIN_SUCCESS").get()
        self.assertEqual(event.actor_username, "editor1")
        self.assertEqual(event.actor_id, self.editor.pk)
        self.assertEqual(event.actor_role, "editor")
        self.assertEqual(event.ip_address, "198.51.100.7")
        self.assertEqual(event.status_code, 200)

    def test_failed_login_recorded_for_existing_and_unknown_accounts(self):
        self.login("editor1", password="wrong")
        self.login("ghost-user", password="wrong")
        failed = self.events("LOGIN_FAILED")
        self.assertEqual(failed.count(), 2)
        self.assertTrue(failed.get(actor_username="editor1").details["account_exists"])
        self.assertFalse(failed.get(actor_username="ghost-user").details["account_exists"])
        self.assertFalse(self.events("LOGIN_SUCCESS").exists())

    def test_invalid_refresh_token_recorded(self):
        self.client.post("/api/token/refresh/", {"refresh": "forged.token.value"}, format="json")
        self.assertTrue(self.events("TOKEN_REFRESH_FAILED").exists())

    def test_rate_limited_response_recorded(self):
        request = RequestFactory().get("/api/assets/", REMOTE_ADDR="192.0.2.50")
        AuditMiddleware(lambda r: HttpResponse(status=429))(request)
        event = self.events("RATE_LIMITED").get()
        self.assertEqual(event.ip_address, "192.0.2.50")


class AccessControlEventTests(AuditTestCase):
    def test_unauthenticated_request_recorded(self):
        self.client.get("/api/users/")
        event = self.events("ACCESS_DENIED").get()
        self.assertEqual(event.status_code, 401)
        self.assertEqual(event.actor_username, "anonymous")

    def test_forbidden_request_recorded_with_user(self):
        self.auth_as(self.viewer)
        self.client.delete("/api/categories/999/")
        event = self.events("ACCESS_DENIED").get()
        self.assertEqual(event.status_code, 403)
        self.assertEqual(event.actor_username, "viewer1")
        self.assertEqual(event.method, "DELETE")


class AssetEventTests(AuditTestCase):
    def upload(self):
        response = self.client.post(
            "/api/assets/", {"title": "Brand logo", "file": self.png()}, format="multipart"
        )
        self.assertEqual(response.status_code, 201, response.content)
        return Asset.objects.get(pk=response.data["id"])

    def test_upload_recorded_with_actor_and_file(self):
        self.auth_as(self.admin)
        asset = self.upload()
        event = self.events("ASSET_UPLOADED").get()
        self.assertEqual(event.actor_username, "admin1")
        self.assertEqual(event.target_id, str(asset.pk))
        self.assertIn("logo", event.details["file"])

    def test_view_and_delete_recorded(self):
        self.auth_as(self.admin)
        asset = self.upload()
        self.client.get(f"/api/assets/{asset.pk}/")
        self.client.delete(f"/api/assets/{asset.pk}/")
        self.assertEqual(self.events("ASSET_VIEWED").get().target_id, str(asset.pk))
        deleted = self.events("ASSET_DELETED").get()
        self.assertEqual(deleted.target_id, str(asset.pk))
        self.assertEqual(deleted.actor_username, "admin1")

    def test_version_submit_and_approval_recorded(self):
        self.auth_as(self.admin)
        asset = self.upload()
        self.auth_as(self.editor)
        response = self.client.post(
            f"/api/assets/{asset.pk}/request_update/",
            {"title": "Brand logo v2", "file": self.png("logo2.png")}, format="multipart",
        )
        self.assertEqual(response.status_code, 201, response.content)
        submitted = self.events("VERSION_SUBMITTED").get()
        self.assertEqual(submitted.actor_username, "editor1")

        self.auth_as(self.admin)
        self.client.patch(f"/api/versions/{response.data['id']}/", {"status": "approved"}, format="json")
        approved = self.events("VERSION_APPROVED").get()
        self.assertEqual(approved.actor_username, "admin1")
        self.assertEqual(approved.details["to"], "approved")


class AdministrationEventTests(AuditTestCase):
    def test_role_escalation_recorded_as_high_severity(self):
        self.auth_as(self.admin)
        response = self.client.patch(f"/api/users/{self.viewer.pk}/", {"role": "admin"}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        event = self.events("ROLE_CHANGED").get()
        self.assertEqual(event.severity, "high")
        self.assertEqual(event.details, {"from": "viewer", "to": "admin"})
        self.assertEqual(event.actor_username, "admin1")
        self.assertEqual(event.target_repr, "viewer1 (admin)")

    def test_password_change_recorded_without_hash(self):
        self.viewer.set_password("N3w-Passw0rd-Value!")
        self.viewer.save()
        event = self.events("PASSWORD_CHANGED").get()
        self.assertNotIn("pbkdf2", event.canonical())
        self.assertNotIn("md5$", event.canonical())

    def test_login_bookkeeping_not_logged_as_user_update(self):
        self.login("viewer1")
        self.assertFalse(self.events("USER_UPDATED").exists())

    def test_category_and_tag_changes_recorded(self):
        category = Category.objects.create(name="Logos")
        category.name = "Brand logos"
        category.save()
        category.delete()
        Tag.objects.create(name="draft")
        self.assertTrue(self.events("CATEGORY_CREATED").exists())
        self.assertEqual(self.events("CATEGORY_UPDATED").get().details, {"from": "Logos", "to": "Brand logos"})
        self.assertTrue(self.events("CATEGORY_DELETED").exists())
        self.assertTrue(self.events("TAG_CREATED").exists())

    def test_user_deletion_keeps_history(self):
        self.login("viewer1")
        viewer_id = self.viewer.pk
        self.viewer.delete()
        self.assertTrue(self.events("USER_DELETED").filter(target_id=str(viewer_id)).exists())
        # Earlier events by the deleted user are untouched
        self.assertEqual(SecurityEvent.objects.filter(actor_id=viewer_id, event_type="LOGIN_SUCCESS").count(), 1)
