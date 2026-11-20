"""Live regression retest of the merged DAM backend (secure-demo settings).

Run from the project root:   python security_tests/retest_live.py

It starts the real Django server on a scratch SQLite database, seeds four demo
users, then sends real HTTP requests. A forwarded-proto header stands in for
the Caddy proxy (the backend trusts it only from loopback). TLS 1.3 itself and
PostgreSQL are NOT covered; those need the production-like environment.
Writes retest-results.json next to this script.
"""
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path[:0] = [str(HERE), str(ROOT)]
import secrets
os.environ["RETEST_SECRET"] = secrets.token_urlsafe(64)  # same key for the server subprocess
os.environ["RETEST_WORKDIR"] = tempfile.mkdtemp(prefix="dam_retest_")
os.environ["DJANGO_SETTINGS_MODULE"] = "retest_settings"
PORT = 8011
API = f"http://127.0.0.1:{PORT}"
PW = "Retest-Passw0rd!2026"

import django  # noqa: E402
django.setup()
from django.core.management import call_command  # noqa: E402
call_command("migrate", verbosity=0)
from assets.models import User  # noqa: E402
from rest_framework_simplejwt.tokens import RefreshToken  # noqa: E402

roles = {"admin_demo": ("admin", True), "editor_demo": ("editor", False),
         "editor2_demo": ("editor", False), "viewer_demo": ("viewer", False)}
tokens = {}
for name, (role, staff) in roles.items():
    u = User.objects.create_user(name, f"{name}@example.test", PW, role=role, is_staff=staff)
    r = RefreshToken.for_user(u)
    tokens[name] = {"access": str(r.access_token), "refresh": str(r), "id": u.id}

env = {**os.environ, "PYTHONPATH": os.pathsep.join([str(HERE), str(ROOT)])}
server = subprocess.Popen([sys.executable, "manage.py", "runserver", f"127.0.0.1:{PORT}", "--noreload"],
                          cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
results = []


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect)


def req(method, path, body=None, token=None, raw=None, ctype="application/json", https=True, headers=None):
    h = {"Content-Type": ctype, **(headers or {})}
    if https:
        h["X-Forwarded-Proto"] = "https"
    if token:
        h["Authorization"] = f"Bearer {token}"
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    r = urllib.request.Request(API + path, method=method, data=data, headers=h)
    try:
        with opener.open(r, timeout=30) as resp:
            return resp.status, dict(resp.headers), resp.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()


def multipart(fields, filename, content, ctype):
    b = "----retest"
    parts = b"".join(f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
                     for k, v in fields.items())
    parts += (f'--{b}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\n'
              f"Content-Type: {ctype}\r\n\r\n").encode() + content + f"\r\n--{b}--\r\n".encode()
    return parts, f"multipart/form-data; boundary={b}"


def check(cid, title, status, detail, passed):
    results.append({"id": cid, "title": title, "status": status, "detail": str(detail)[:200],
                    "result": "PASS" if passed else "FAIL"})
    print(f"{cid} {'PASS' if passed else 'FAIL'} [{status}] {title}  ({str(detail)[:80]})")


def main():
    for _ in range(60):
        try:
            req("GET", "/api/does-not-exist/")
            break
        except Exception:
            time.sleep(0.5)
    admin, editor, editor2, viewer = (tokens[n]["access"] for n in
                                      ("admin_demo", "editor_demo", "editor2_demo", "viewer_demo"))
    PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64
    cat = json.loads(req("POST", "/api/categories/", {"name": "Retest"}, token=admin)[2])["id"]
    body, ct = multipart({"title": "Admin asset", "description": "owned by admin", "category_id": cat}, "brand.png", PNG, "image/png")
    s, _, b = req("POST", "/api/assets/", token=admin, raw=body, ctype=ct)
    asset = json.loads(b)
    aid = asset["id"]
    body, ct = multipart({"title": "v2", "category_id": cat}, "brand2.png", PNG + b"1", "image/png")
    s, _, b = req("POST", f"/api/assets/{aid}/request_update/", token=admin, raw=body, ctype=ct)
    vid = json.loads(b)["id"]

    s, _, b = req("GET", "/api/assets/")
    check("R01", "Anonymous user cannot list assets", s, b[:60], s == 401)
    fp = asset["file"]
    fp = fp[fp.index("/media"):] if "/media" in fp else fp
    s, _, b = req("GET", fp)
    check("R02", "Anonymous user cannot open a stored file by direct URL", s, fp, s in (401, 403, 404))
    s, _, b = req("PUT", f"/api/versions/{vid}/", {"status": "approved", "version": 2, "asset": aid}, token=viewer)
    check("R03", "Viewer cannot approve a version (PUT)", s, b[:60], s == 403)
    s, _, b = req("DELETE", f"/api/versions/{vid}/", token=viewer)
    check("R04", "Viewer cannot delete another user's version", s, b[:60], s in (403, 404))
    s, _, b = req("PATCH", f"/api/assets/{aid}/", {"title": "Defaced"}, token=editor)
    check("R05", "Editor cannot edit an asset owned by admin", s, b[:60], s in (403, 404))
    tag = json.loads(req("POST", "/api/tags/", {"name": f"t{int(time.time())}"}, token=admin)[2])
    s, _, b = req("DELETE", f"/api/tags/{tag['id']}/", token=viewer)
    check("R06", "Viewer cannot delete a tag", s, b[:60], s == 403)
    s, _, b = req("PATCH", f"/api/users/{tokens['editor_demo']['id']}/", {"role": "admin"}, token=editor)
    check("R07", "Editor cannot promote own role to admin", s, b[:60], s == 403)
    body, ct = multipart({"title": "evil"}, "evil.html", b"<html><script>alert(1)</script></html>", "text/html")
    s, _, b = req("POST", "/api/assets/", token=admin, raw=body, ctype=ct)
    check("R08", "HTML file with script is rejected on upload", s, b[:60], s == 400)
    s, _, b = req("POST", "/api/categories/", {"name": "<script>alert('xss')</script>"}, token=admin)
    check("R09", "Script payload in category name is rejected", s, b[:60], s == 400)
    s, _, b = req("GET", "/api/does-not-exist/")
    check("R10", "Unknown URL gives a generic 404 (no debug page)", s,
          "generic" if b"URLconf" not in b else "debug page",
          s == 404 and b"URLconf" not in b and b"DEBUG = True" not in b)
    s, h, _ = req("GET", "/api/assets/", token=admin)
    h = {k.lower(): v for k, v in h.items()}
    want = {"x-content-type-options": "nosniff", "x-frame-options": "DENY",
            "strict-transport-security": None, "referrer-policy": None}
    miss = [k for k, v in want.items() if k not in h or (v and v.lower() != h[k].lower())]
    check("R11", "Security headers present (nosniff, frame deny, HSTS, referrer)", s, f"missing={miss}", not miss)
    s, h, _ = req("GET", "/api/assets/", https=False)
    loc = {k.lower(): v for k, v in h.items()}.get("location", "")
    check("R12", "Plain HTTP request is redirected to HTTPS", s, loc, s == 301 and loc.startswith("https://"))
    s, _, b = req("POST", "/api/users/", {"username": f"weak{int(time.time())}", "password": "123", "role": "viewer"},
                  token=admin)
    check("R13", "Weak password is rejected on user creation", s, b[:60], s == 400)
    refresh = tokens["viewer_demo"]["refresh"]
    s, _, _ = req("POST", "/api/logout/", {"refresh": refresh}, token=viewer)
    s2, _, _ = req("POST", "/api/token/refresh/", {"refresh": refresh})
    check("R14", "Logout revokes the refresh token", s, f"logout={s}, refresh-after={s2}",
          s in (200, 204, 205) and s2 == 401)
    s, _, b = req("GET", "/api/audit/events/", token=viewer)
    check("R15", "Viewer cannot read the audit log", s, b[:60], s == 403)
    codes = [req("POST", "/api/token/", {"username": "viewer_demo", "password": f"guess{i}"})[0] for i in range(8)]
    check("R16", "Login rate limit: 6th wrong attempt gets 429", codes[5], f"codes={codes}",
          codes[:5] == [401] * 5 and codes[5] == 429)
    summary = json.loads(req("GET", "/api/audit/summary/", token=admin)[2])
    alerts = {a["event_type"] for a in summary["recent_alerts"]}
    check("R17", "Brute-force attack raised an alert (429s counted)", 200, sorted(alerts),
          "BRUTE_FORCE_SUSPECTED" in alerts)
    integ = json.loads(req("GET", "/api/audit/integrity/", token=admin)[2])
    check("R18", "Audit hash chain intact after attack traffic", 200, json.dumps(integ), integ.get("intact") is True)


try:
    main()
finally:
    server.terminate()
n = sum(r["result"] == "PASS" for r in results)
print(f"\n{n} of {len(results)} checks passed")
(HERE / "retest-results.json").write_text(json.dumps(results, indent=1))
sys.exit(0 if n == len(results) else 1)
