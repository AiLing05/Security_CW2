"""
Sanitisation for anything written to the audit trail.

- Secrets (passwords, JWTs, keys, cookies) are replaced with [REDACTED].
- CR/LF and control characters are removed to stop log forging (CWE-117).
- Strings and collections are size-limited so a request cannot flood the log.
"""
import re

REDACTED = "[REDACTED]"
MAX_STRING = 256
MAX_ITEMS = 25
MAX_DEPTH = 4

SENSITIVE_KEY = re.compile(
    r"pass(word|wd)?|secret|token|access|refresh|authori[sz]ation|cookie|session|api[_-]?key|csrf|signature",
    re.IGNORECASE,
)
# A JWT looks like three base64url sections separated by dots
JWT_PATTERN = re.compile(r"eyJ[\w-]+\.[\w-]+\.[\w-]+")
CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")


def clean_text(value, limit=MAX_STRING):
    """Return a single-line, length-limited string safe to store and display."""
    if value is None:
        return ""
    text = str(value)
    text = JWT_PATTERN.sub(REDACTED, text)
    text = CONTROL_CHARS.sub(" ", text)
    if len(text) > limit:
        text = text[: limit - 3] + "..."
    return text


def sanitize(value, depth=0):
    """Recursively sanitise a JSON-compatible value for the `details` field."""
    if depth > MAX_DEPTH:
        return "[TRUNCATED]"
    if isinstance(value, dict):
        out = {}
        for i, (key, item) in enumerate(value.items()):
            if i >= MAX_ITEMS:
                out["_truncated"] = True
                break
            key = clean_text(key, 64)
            out[key] = REDACTED if SENSITIVE_KEY.search(key) else sanitize(item, depth + 1)
        return out
    if isinstance(value, (list, tuple, set)):
        return [sanitize(item, depth + 1) for item in list(value)[:MAX_ITEMS]]
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return clean_text(value)
