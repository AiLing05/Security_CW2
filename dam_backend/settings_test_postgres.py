"""Isolated PostgreSQL tests using local .env; never use as server settings."""
from .settings import *  # noqa: F403,F401

SECURE_DEMO = False
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0
AUDIT_TRUSTED_PROXY_COUNT = 0
ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'testserver']
# Django creates/destroys this separate DB, never the running application's DB.
DATABASES['default']['TEST'] = {'NAME': 'test_ruth_authorization'}  # noqa: F405
