"""Configure local Django development without overwriting existing secrets."""
from pathlib import Path
from django.core.management.utils import get_random_secret_key
from cryptography.fernet import Fernet
import re
root = Path(__file__).resolve().parent
path = root / '.env'
contents = path.read_text(encoding='utf-8') if path.exists() else ''
def set_missing_or_blank(key, value):
    global contents
    pattern = rf'(?m)^\s*{re.escape(key)}\s*=\s*([^\r\n]*)$'
    match = re.search(pattern, contents)
    if match:
        if match.group(1).strip(): return
        contents = contents[:match.start()] + f'{key}={value}' + contents[match.end():]
    else:
        contents += ('\n' if contents and not contents.endswith('\n') else '') + f'{key}={value}\n'
set_missing_or_blank('SECRET_KEY', get_random_secret_key())
set_missing_or_blank('ENCRYPTION_KEY', Fernet.generate_key().decode('ascii'))
pattern = r'(?m)^\s*DEBUG\s*=\s*[^\r\n]*$'
if re.search(pattern, contents): contents = re.sub(pattern, 'DEBUG=True', contents)
else: contents += ('\n' if contents and not contents.endswith('\n') else '') + 'DEBUG=True\n'
path.write_text(contents, encoding='utf-8')
print('Local .env configured (DEBUG=True). Existing keys preserved. No secrets printed.')
print('Never commit .env. Do not use DEBUG=True in production.')
