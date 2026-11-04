"""Validated infrastructure configuration; never include values in errors."""
import os
from django.core.exceptions import ImproperlyConfigured


def required(name):
    value = os.environ.get(name, "").strip()
    if not value or value.startswith("CHANGE_ME"):
        raise ImproperlyConfigured(f"Set {name} to a private value before startup.")
    return value


def boolean(name, default=False):
    value = os.environ.get(name, str(default)).lower()
    if value not in {"true", "false"}:
        raise ImproperlyConfigured(f"{name} must be true or false.")
    return value == "true"


def csv(name, default):
    return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]
