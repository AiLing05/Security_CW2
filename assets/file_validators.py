from pathlib import Path
from rest_framework.exceptions import ValidationError

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
ALLOWED_TYPES = {
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
    ".png": {"image/png"},
    ".gif": {"image/gif"},
    ".webp": {"image/webp"},
    ".pdf": {"application/pdf"},
    ".mp4": {"video/mp4"},
    ".glb": {"model/gltf-binary", "application/octet-stream"},
}

def validate_uploaded_file(file):
    if file is None:
        raise ValidationError("Please select a file.")

    # File size
    if file.size == 0:
        raise ValidationError("Empty files are not allowed.")

    if file.size > MAX_FILE_SIZE:
        raise ValidationError("File size must not exceed 50 MB.")

    # Extension
    extension = Path(file.name).suffix.lower()

    if extension not in ALLOWED_TYPES:
        raise ValidationError("This file type is not supported. Please select a supported file.")

    # MIME type
    mime = getattr(file, "content_type", "") or ""
    mime = mime.lower().split(";")[0].strip()

    if mime not in ALLOWED_TYPES[extension]:
        raise ValidationError(
            "File MIME type does not match the extension."
        )

    # File signature
    file.seek(0)
    header = file.read(32)
    file.seek(0)

    checks = {
        ".jpg": lambda h: h.startswith(b"\xff\xd8\xff"),
        ".jpeg": lambda h: h.startswith(b"\xff\xd8\xff"),
        ".png": lambda h: h.startswith(b"\x89PNG\r\n\x1a\n"),
        ".gif": lambda h: h.startswith((b"GIF87a", b"GIF89a")),
        ".webp": lambda h: h.startswith(b"RIFF") and h[8:12] == b"WEBP",
        ".pdf": lambda h: h.startswith(b"%PDF-"),
        ".mp4": lambda h: len(h) >= 12 and h[4:8] == b"ftyp",
        ".glb": lambda h: h.startswith(b"glTF"),
    }

    if not checks[extension](header):
        raise ValidationError(
            "File content does not match the expected format."
        )

    return file
