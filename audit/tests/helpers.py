import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from audit.models import SecurityEvent

User = get_user_model()
PASSWORD = "Str0ng-Test-Passw0rd!"

_MEDIA = tempfile.mkdtemp(prefix="dam-test-media-")


@override_settings(MEDIA_ROOT=_MEDIA)
class AuditTestCase(TestCase):
    """Creates one user per DAM role and gives helpers for API calls."""

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(_MEDIA, ignore_errors=True)

    def setUp(self):
        cache.clear()  # reset the login rate limit between tests
        self.admin = User.objects.create_superuser("admin1", "admin1@example.com", PASSWORD)
        self.editor = User.objects.create_user("editor1", "editor1@example.com", PASSWORD, role="editor")
        self.viewer = User.objects.create_user("viewer1", "viewer1@example.com", PASSWORD, role="viewer")
        self.client = APIClient(REMOTE_ADDR="203.0.113.10")

    def login(self, username, password=PASSWORD, ip="203.0.113.10"):
        return self.client.post(
            "/api/token/", {"username": username, "password": password}, format="json", REMOTE_ADDR=ip
        )

    def auth_as(self, user, ip="203.0.113.10"):
        response = self.login(user.username, ip=ip)
        self.assertEqual(response.status_code, 200, response.content)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        return response.data

    def events(self, event_type):
        return SecurityEvent.objects.filter(event_type=event_type)

    @staticmethod
    def png(name="logo.png"):
        # Minimal valid PNG header + payload
        return SimpleUploadedFile(name, b"\x89PNG\r\n\x1a\n" + b"0" * 64, content_type="image/png")
