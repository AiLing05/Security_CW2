import uuid
from pathlib import Path


def secure_asset_path(instance, filename):
    extension = Path(filename).suffix.lower()
    new_filename = f"{uuid.uuid4().hex}{extension}"
    return f"assets/{new_filename}"


def secure_version_path(instance, filename):
    extension = Path(filename).suffix.lower()
    new_filename = f"{uuid.uuid4().hex}{extension}"
    return f"assets/versions/{new_filename}"
