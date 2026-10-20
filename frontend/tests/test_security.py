import shutil
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from unittest.mock import patch

from Filedigital.models import (
    AccessRequest,
    File,
    FileActivityLog,
)

User = get_user_model()

TEST_PASSWORD = "SecureTestPassword2026!"


class VaultDeskSecurityTests(TestCase):
    """
    Automated tests for VaultDesk authentication,
    session security, document management, and permissions.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Uploaded test files are stored outside the real media folder.
        cls.temp_media = tempfile.mkdtemp(prefix="vaultdesk_tests_")
        cls.media_override = override_settings(
            MEDIA_ROOT=cls.temp_media,
            EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        )
        cls.media_override.enable()

    @classmethod
    def tearDownClass(cls):
        cls.media_override.disable()
        shutil.rmtree(cls.temp_media, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.firebase_patcher = patch(
            "firebase_app.signals.generate_firebase_auth_key",
            return_value="mock-test-token",
        )
        self.firebase_patcher.start()
        self.addCleanup(self.firebase_patcher.stop)

        self.user_group = Group.objects.create(name="User")
        self.manager_group = Group.objects.create(name="Manager")

        self.user = self.create_user(
            email="user1@example.com",
            name="User One",
            role=self.user_group,
        )

        self.other_user = self.create_user(
            email="user2@example.com",
            name="User Two",
            role=self.user_group,
        )

        self.manager = self.create_user(
            email="manager@example.com",
            name="Manager",
            role=self.manager_group,
            is_staff=True,
        )


    def create_user(self, email, name, role, **extra):
        user = User.objects.create_user(
            email=email,
            password=TEST_PASSWORD,
            name=name,
            phone="0123456789",
            location="Penang",
            role=role,
            **extra,
        )
        user.groups.add(role)
        return user

    def create_document(
            self,
            owner=None,
            name="Test Document",
            visibility="private",
            approved=False,
    ):
        if owner is None:
            owner = self.user

        uploaded_file = SimpleUploadedFile(
            "test_document.txt",
            b"This is a test document.",
            content_type="text/plain",
        )

        return File.objects.create(
            name=name,
            file=uploaded_file,
            uploaded_by=owner,
            file_type=visibility,
            is_approved=approved,
        )

    # --------------------------------------------------
    # AUTHENTICATION TESTS
    # --------------------------------------------------

    def test_01_login_with_valid_credentials(self):
        response = self.client.post(
            reverse("frontend:login"),
            {
                "email": self.user.email,
                "password": TEST_PASSWORD,
            },
        )

        self.assertRedirects(
            response,
            reverse("frontend:dashboard"),
        )

        self.assertEqual(
            str(self.client.session["_auth_user_id"]),
            str(self.user.pk),
        )

    def test_02_login_with_wrong_password(self):
        response = self.client.post(
            reverse("frontend:login"),
            {
                "email": self.user.email,
                "password": "IncorrectPassword123!",
            },
        )

        self.assertEqual(response.status_code, 200)

        self.assertNotIn(
            "_auth_user_id",
            self.client.session,
        )

    def test_03_password_is_hashed(self):
        self.assertNotEqual(
            self.user.password,
            TEST_PASSWORD,
        )

        self.assertTrue(
            self.user.check_password(TEST_PASSWORD),
        )

    def test_04_registration_success(self):
        response = self.client.post(
            reverse("frontend:register"),
            {
                "email": "newuser@example.com",
                "name": "New User",
                "phone": "0123456789",
                "location": "Penang",
                "password": TEST_PASSWORD,
                "confirm_password": TEST_PASSWORD,
            },
        )

        self.assertRedirects(
            response,
            reverse("frontend:dashboard"),
        )

        new_user = User.objects.get(
            email="newuser@example.com"
        )

        self.assertTrue(
            new_user.check_password(TEST_PASSWORD)
        )

    def test_05_registration_rejects_duplicate_email(self):
        original_count = User.objects.count()

        self.client.post(
            reverse("frontend:register"),
            {
                "email": self.user.email,
                "name": "Duplicate User",
                "phone": "0123456789",
                "location": "Penang",
                "password": TEST_PASSWORD,
                "confirm_password": TEST_PASSWORD,
            },
        )

        self.assertEqual(
            User.objects.count(),
            original_count,
        )

    def test_06_registration_rejects_mismatched_passwords(self):
        response = self.client.post(
            reverse("frontend:register"),
            {
                "email": "mismatch@example.com",
                "name": "Mismatch",
                "phone": "0123456789",
                "location": "Penang",
                "password": TEST_PASSWORD,
                "confirm_password": "DifferentPassword2026!",
            },
        )

        self.assertEqual(response.status_code, 200)

        self.assertFalse(
            User.objects.filter(
                email="mismatch@example.com"
            ).exists()
        )

    # --------------------------------------------------
    # SESSION SECURITY TESTS
    # --------------------------------------------------

    def test_07_logout_invalidates_session(self):
        self.client.force_login(self.user)

        self.assertIn(
            "_auth_user_id",
            self.client.session,
        )

        response = self.client.post(
            reverse("frontend:logout")
        )

        self.assertRedirects(
            response,
            reverse("frontend:login"),
        )

        self.assertNotIn(
            "_auth_user_id",
            self.client.session,
        )

    def test_08_dashboard_requires_login(self):
        response = self.client.get(
            reverse("frontend:dashboard")
        )

        self.assertRedirects(
            response,
            reverse("frontend:login")
            + "?next="
            + reverse("frontend:dashboard"),
        )

    def test_09_documents_require_login(self):
        response = self.client.get(
            reverse("frontend:documents")
        )

        self.assertEqual(response.status_code, 302)

        self.assertIn(
            reverse("frontend:login"),
            response.url,
        )

    def test_10_upload_requires_login(self):
        response = self.client.get(
            reverse("frontend:upload")
        )

        self.assertEqual(response.status_code, 302)

    def test_11_logout_requires_post(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("frontend:logout")
        )

        self.assertEqual(response.status_code, 405)

        self.assertIn(
            "_auth_user_id",
            self.client.session,
        )

    # --------------------------------------------------
    # DOCUMENT UPLOAD TESTS
    # --------------------------------------------------

    def test_12_upload_valid_document(self):
        self.client.force_login(self.user)

        uploaded_file = SimpleUploadedFile(
            "report.pdf",
            b"%PDF-1.4 test content",
            content_type="application/pdf",
        )

        response = self.client.post(
            reverse("frontend:upload"),
            {
                "name": "Security Report",
                "file": uploaded_file,
                "file_type": "private",
            },
        )

        self.assertRedirects(
            response,
            reverse("frontend:documents"),
        )

        self.assertTrue(
            File.objects.filter(
                name="Security Report",
                uploaded_by=self.user,
            ).exists()
        )

    def test_13_upload_rejects_invalid_extension(self):
        self.client.force_login(self.user)

        uploaded_file = SimpleUploadedFile(
            "malicious.exe",
            b"fake executable",
            content_type="application/octet-stream",
        )

        response = self.client.post(
            reverse("frontend:upload"),
            {
                "name": "Malicious File",
                "file": uploaded_file,
                "file_type": "private",
            },
        )

        self.assertEqual(response.status_code, 200)

        self.assertFalse(
            File.objects.filter(
                name="Malicious File"
            ).exists()
        )

    def test_14_upload_rejects_oversized_file(self):
        self.client.force_login(self.user)

        oversized_file = SimpleUploadedFile(
            "large.txt",
            b"A" * (10 * 1024 * 1024 + 1),
            content_type="text/plain",
        )

        response = self.client.post(
            reverse("frontend:upload"),
            {
                "name": "Oversized File",
                "file": oversized_file,
                "file_type": "private",
            },
        )

        self.assertEqual(response.status_code, 200)

        self.assertFalse(
            File.objects.filter(
                name="Oversized File"
            ).exists()
        )

    def test_15_upload_defaults_invalid_visibility_to_private(self):
        self.client.force_login(self.user)

        uploaded_file = SimpleUploadedFile(
            "visibility.txt",
            b"Test content",
            content_type="text/plain",
        )

        self.client.post(
            reverse("frontend:upload"),
            {
                "name": "Visibility Test",
                "file": uploaded_file,
                "file_type": "administrator",
            },
        )

        document = File.objects.get(
            name="Visibility Test"
        )

        self.assertEqual(
            document.file_type,
            "private",
        )

    # --------------------------------------------------
    # DOCUMENT ACCESS CONTROL TESTS
    # --------------------------------------------------

    def test_16_owner_can_download_private_document(self):
        document = self.create_document()

        self.client.force_login(self.user)

        response = self.client.get(
            reverse(
                "frontend:download",
                args=[document.pk],
            )
        )

        self.assertEqual(response.status_code, 200)

        # Close streaming response to release file handle.
        response.close()

    def test_17_other_user_cannot_download_private_document(self):
        document = self.create_document()

        self.client.force_login(self.other_user)

        response = self.client.get(
            reverse(
                "frontend:download",
                args=[document.pk],
            )
        )

        self.assertIn(
            response.status_code,
            [403, 404],
        )

    def test_18_approved_public_document_is_accessible(self):
        document = self.create_document(
            visibility="public",
            approved=True,
        )

        self.client.force_login(self.other_user)

        response = self.client.get(
            reverse(
                "frontend:download",
                args=[document.pk],
            )
        )

        self.assertEqual(response.status_code, 200)
        response.close()

    def test_19_unapproved_public_document_is_restricted(self):
        document = self.create_document(
            visibility="public",
            approved=False,
        )

        self.client.force_login(self.other_user)

        response = self.client.get(
            reverse(
                "frontend:download",
                args=[document.pk],
            )
        )

        self.assertIn(
            response.status_code,
            [403, 404],
        )

    def test_20_user_cannot_delete_another_users_document(self):
        document = self.create_document()

        self.client.force_login(self.other_user)

        response = self.client.post(
            reverse(
                "frontend:delete",
                args=[document.pk],
            )
        )

        self.assertIn(
            response.status_code,
            [403, 404],
        )

        self.assertTrue(
            File.objects.filter(
                pk=document.pk
            ).exists()
        )

    def test_21_owner_can_delete_document(self):
        document = self.create_document()

        self.client.force_login(self.user)

        response = self.client.post(
            reverse(
                "frontend:delete",
                args=[document.pk],
            )
        )

        self.assertRedirects(
            response,
            reverse("frontend:documents"),
        )

        self.assertFalse(
            File.objects.filter(
                pk=document.pk
            ).exists()
        )

    # --------------------------------------------------
    # ROLE-BASED ACCESS CONTROL TESTS
    # --------------------------------------------------

    def test_22_normal_user_cannot_open_approvals(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("frontend:approvals")
        )

        self.assertEqual(response.status_code, 403)

    def test_23_normal_user_cannot_open_reports(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("frontend:reports")
        )

        self.assertEqual(response.status_code, 403)

    def test_24_manager_can_open_approvals(self):
        self.client.force_login(self.manager)

        response = self.client.get(
            reverse("frontend:approvals")
        )

        self.assertEqual(response.status_code, 200)

    def test_25_manager_can_open_reports(self):
        self.client.force_login(self.manager)

        response = self.client.get(
            reverse("frontend:reports")
        )

        self.assertEqual(response.status_code, 200)

    def test_26_normal_user_cannot_approve_document(self):
        document = self.create_document()

        self.client.force_login(self.user)

        response = self.client.post(
            reverse(
                "frontend:approve_document",
                args=[document.pk],
            ),
            {"decision": "approve"},
        )

        self.assertEqual(response.status_code, 403)

        document.refresh_from_db()

        self.assertFalse(document.is_approved)

    def test_27_manager_can_approve_document(self):
        document = self.create_document()

        self.client.force_login(self.manager)

        response = self.client.post(
            reverse(
                "frontend:approve_document",
                args=[document.pk],
            ),
            {"decision": "approve"},
        )

        self.assertRedirects(
            response,
            reverse("frontend:approvals"),
        )

        document.refresh_from_db()

        self.assertTrue(document.is_approved)

    # --------------------------------------------------
    # ACCESS REQUEST TESTS
    # --------------------------------------------------

    def test_28_user_can_request_private_document_access(self):
        document = self.create_document()

        self.client.force_login(self.other_user)

        response = self.client.post(
            reverse("frontend:access"),
            {"file_id": document.pk},
        )

        self.assertRedirects(
            response,
            reverse("frontend:access"),
        )

        self.assertTrue(
            AccessRequest.objects.filter(
                requester=self.other_user,
                file=document,
            ).exists()
        )

    def test_29_manager_can_approve_access_request(self):
        document = self.create_document()

        access_request = AccessRequest.objects.create(
            requester=self.other_user,
            file=document,
        )

        self.client.force_login(self.manager)

        response = self.client.post(
            reverse(
                "frontend:review_access",
                args=[access_request.pk],
            ),
            {"decision": "approve"},
        )

        self.assertRedirects(
            response,
            reverse("frontend:access"),
        )

        access_request.refresh_from_db()

        self.assertTrue(access_request.is_approved)

    def test_30_normal_user_cannot_approve_access_request(self):
        document = self.create_document()

        access_request = AccessRequest.objects.create(
            requester=self.other_user,
            file=document,
        )

        self.client.force_login(self.user)

        response = self.client.post(
            reverse(
                "frontend:review_access",
                args=[access_request.pk],
            ),
            {"decision": "approve"},
        )

        self.assertEqual(response.status_code, 403)

        access_request.refresh_from_db()

        self.assertIsNone(access_request.is_approved)

    # --------------------------------------------------
    # AUDIT LOG TESTS
    # --------------------------------------------------

    def test_31_upload_creates_audit_log(self):
        self.client.force_login(self.user)

        uploaded_file = SimpleUploadedFile(
            "audit.txt",
            b"Audit test",
            content_type="text/plain",
        )

        self.client.post(
            reverse("frontend:upload"),
            {
                "name": "Audit Document",
                "file": uploaded_file,
                "file_type": "private",
            },
        )

        self.assertTrue(
            FileActivityLog.objects.filter(
                user=self.user,
                action="upload",
            ).exists()
        )

    def test_32_download_creates_audit_log(self):
        document = self.create_document()

        self.client.force_login(self.user)

        response = self.client.get(
            reverse(
                "frontend:download",
                args=[document.pk],
            )
        )

        self.assertEqual(response.status_code, 200)
        response.close()

        self.assertTrue(
            FileActivityLog.objects.filter(
                user=self.user,
                file=document,
                action="download",
            ).exists()
        )
