"""
Settings for running the automated test suite without a PostgreSQL server.

    python manage.py test --settings=dam_backend.settings_test

PostgreSQL-only checks (the audit trigger) are skipped on SQLite; run the
suite with the normal settings to include them.
"""
import os
from unittest.mock import patch

# Never depend on the developer's private .env or point tests at their database.
with patch.dict(os.environ, {
    "PYTHON_DOTENV_DISABLED": "1",
    "DJANGO_SECRET_KEY": "test-only-key-never-use-for-a-real-deployment-1234567890",
    "DJANGO_SECURE_DEMO": "false", "DJANGO_DEBUG": "false",
    "DJANGO_ALLOWED_HOSTS": "localhost,127.0.0.1,testserver",
    "POSTGRES_DB": "test", "POSTGRES_USER": "test", "POSTGRES_PASSWORD": "test",
    "POSTGRES_HOST": "127.0.0.1", "POSTGRES_SSLMODE": "disable",
}):
    from .settings import *  # noqa: F401,F403,E402

# Tests of application behavior use plain HTTP; infrastructure tests override this.
SECURE_DEMO = False
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0
AUDIT_TRUSTED_PROXY_COUNT = 0

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "test_db.sqlite3",  # noqa: F405
    }
}
