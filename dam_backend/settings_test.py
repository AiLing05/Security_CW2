"""
Settings for running the automated test suite without a PostgreSQL server.

    python manage.py test --settings=dam_backend.settings_test

PostgreSQL-only checks (the audit trigger) are skipped on SQLite; run the
suite with the normal settings to include them.
"""
from .settings import *  # noqa: F401,F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "test_db.sqlite3",  # noqa: F405
    }
}
