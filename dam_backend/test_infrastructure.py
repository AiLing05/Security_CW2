"""Infrastructure tests use no shared database or real credentials."""
import os
import subprocess
import sys
from unittest.mock import patch

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponse
from django.middleware.csrf import get_token
from django.test import Client, RequestFactory, SimpleTestCase, override_settings
from django.urls import path

from .environment import boolean, required
from .middleware import LocalProxyMiddleware


def csrf_form(request):
    get_token(request)
    return HttpResponse("form")


def session_form(request):
    request.session["infrastructure_test"] = True
    return HttpResponse("session")


urlpatterns = [path("form/", csrf_form), path("session/", session_form)]


class EnvironmentTests(SimpleTestCase):
    def test_secret_errors_do_not_disclose_values(self):
        for value in ("", "CHANGE_ME_private"):
            with patch.dict(os.environ, {"TEST_SECRET": value}):
                with self.assertRaisesMessage(ImproperlyConfigured, "Set TEST_SECRET"):
                    required("TEST_SECRET")

    def test_boolean_typo_fails_closed(self):
        with patch.dict(os.environ, {"DJANGO_DEBUG": "tru"}):
            with self.assertRaises(ImproperlyConfigured):
                boolean("DJANGO_DEBUG")

    def load_settings(self, **changes):
        env = dict(os.environ, DJANGO_SECRET_KEY="test-only-private-random-enough-key-1234567890-abcdefghijklmnop",
                   POSTGRES_DB="test", POSTGRES_USER="test", POSTGRES_PASSWORD="test",
                   DJANGO_DEBUG="false", DJANGO_SECURE_DEMO="true", DJANGO_ALLOWED_HOSTS="localhost",
                   POSTGRES_HOST="127.0.0.1", POSTGRES_SSLMODE="disable", PYTHON_DOTENV_DISABLED="1")
        env.update(changes)
        return subprocess.run([sys.executable, "-c", "import dam_backend.settings as s; "
                               "assert not s.DEBUG; assert s.SESSION_COOKIE_SECURE; "
                               "assert s.CSRF_COOKIE_SECURE; assert s.SECURE_SSL_REDIRECT; "
                               "assert s.SECURE_HSTS_SECONDS == 300"],
                              env=env, capture_output=True, text=True)

    def test_secure_defaults(self):
        result = self.load_settings()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_unsafe_configuration_fails_at_startup(self):
        for change in ({"DJANGO_SECRET_KEY": ""}, {"POSTGRES_PASSWORD": ""},
                       {"DJANGO_DEBUG": "true"}, {"DJANGO_ALLOWED_HOSTS": "*"},
                       {"POSTGRES_HOST": "db.example.org"}, {"POSTGRES_SSLMODE": "require"}):
            with self.subTest(change=list(change)):
                self.assertNotEqual(self.load_settings(**change).returncode, 0)


@override_settings(SECURE_DEMO=True, SECURE_SSL_REDIRECT=True, SECURE_HSTS_SECONDS=300,
                   ALLOWED_HOSTS=["localhost"], CORS_ALLOWED_ORIGINS=["https://localhost:3443"])
class TransportTests(SimpleTestCase):
    def test_http_redirect(self):
        response = self.client.get("/", HTTP_HOST="localhost:8443")
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response["Location"], "https://localhost:8443/")

    def test_https_response_headers(self):
        response = self.client.get("/", secure=True, HTTP_HOST="localhost:8443")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Strict-Transport-Security"], "max-age=300")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response["X-Frame-Options"], "DENY")
        self.assertEqual(response["Referrer-Policy"], "same-origin")

    def test_cors_preflight_allows_only_frontend(self):
        for origin, allowed in (("https://localhost:3443", True), ("https://evil.example", False),
                                ("http://localhost:3000", False)):
            response = self.client.options("/api/assets/", secure=True, HTTP_HOST="localhost:8443",
                                           HTTP_ORIGIN=origin, HTTP_ACCESS_CONTROL_REQUEST_METHOD="GET",
                                           HTTP_ACCESS_CONTROL_REQUEST_HEADERS="authorization")
            self.assertEqual("Access-Control-Allow-Origin" in response, allowed)
            self.assertNotIn("Access-Control-Allow-Credentials", response)

    def test_proxy_scheme_and_spoofing(self):
        factory = RequestFactory()
        for peer, secure in (("127.0.0.1", True), ("203.0.113.7", False)):
            request = factory.get("/", REMOTE_ADDR=peer, HTTP_X_FORWARDED_PROTO="https",
                                  HTTP_X_FORWARDED_FOR="192.0.2.1")
            LocalProxyMiddleware(lambda r: HttpResponse())(request)
            self.assertEqual(request.is_secure(), secure)
            if not secure:
                self.assertNotIn("HTTP_X_FORWARDED_FOR", request.META)

    def test_unknown_host_rejected(self):
        response = self.client.get("/", secure=True, HTTP_HOST="evil.example")
        self.assertEqual(response.status_code, 400)

    def test_admin_post_without_csrf_rejected(self):
        response = Client(enforce_csrf_checks=True).post("/admin/login/", {}, secure=True,
                                                        HTTP_HOST="localhost:8443")
        self.assertEqual(response.status_code, 403)

    @override_settings(ROOT_URLCONF=__name__, SESSION_COOKIE_SECURE=True,
                       SESSION_ENGINE="django.contrib.sessions.backends.signed_cookies")
    def test_session_cookie_attributes(self):
        response = self.client.get("/session/", secure=True, HTTP_HOST="localhost:8443")
        cookie = response.cookies[settings.SESSION_COOKIE_NAME]
        self.assertTrue(cookie["secure"])
        self.assertTrue(cookie["httponly"])
        self.assertEqual(cookie["samesite"], "Lax")

    @override_settings(ROOT_URLCONF=__name__, CSRF_COOKIE_SECURE=True, CSRF_COOKIE_HTTPONLY=True)
    def test_csrf_cookie_and_same_origin_form(self):
        client = Client(enforce_csrf_checks=True)
        response = client.get("/form/", secure=True, HTTP_HOST="localhost:8443")
        cookie = response.cookies[settings.CSRF_COOKIE_NAME]
        self.assertTrue(cookie["secure"])
        self.assertTrue(cookie["httponly"])
        response = client.post("/form/", {"csrfmiddlewaretoken": cookie.value}, secure=True,
                               HTTP_HOST="localhost:8443", HTTP_ORIGIN="https://localhost:8443")
        self.assertEqual(response.status_code, 200)
        response = client.post("/form/", {"csrfmiddlewaretoken": cookie.value}, secure=True,
                               HTTP_HOST="localhost:8443", HTTP_ORIGIN="https://evil.example")
        self.assertEqual(response.status_code, 403)
