"""Settings for the live regression retest: secure-demo mode, scratch SQLite DB and media folder.

Nothing here touches the project's real database, .env or media folder.
"""
import os
import secrets
import tempfile
from pathlib import Path

os.environ.update({
    "PYTHON_DOTENV_DISABLED": "1",
    "DJANGO_SECRET_KEY": os.environ.get("RETEST_SECRET") or secrets.token_urlsafe(64),
    "DJANGO_SECURE_DEMO": "true", "DJANGO_DEBUG": "false",
    "DJANGO_ALLOWED_HOSTS": "localhost,127.0.0.1",
    "POSTGRES_DB": "x", "POSTGRES_USER": "x", "POSTGRES_PASSWORD": "x",
    "POSTGRES_HOST": "127.0.0.1", "POSTGRES_SSLMODE": "disable",
})
from dam_backend.settings import *  # noqa: F401,F403,E402

WORK = Path(os.environ.get("RETEST_WORKDIR") or tempfile.mkdtemp(prefix="dam_retest_"))
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": WORK / "retest.sqlite3"}}
MEDIA_ROOT = WORK / "media"
LOGGING = {"version": 1, "disable_existing_loggers": False}
