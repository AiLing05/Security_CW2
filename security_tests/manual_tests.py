"""Manual OWASP Top 10 (2021) API test cases against the local DAM baseline.

Each case states the secure (expected) behaviour. PASS = secure behaviour
observed. FAIL = vulnerability confirmed (recorded with evidence).

Run (backend on :8000 with the demo users seeded):
    set DAM_DEMO_PASSWORD=<demo user password>
    python security_tests/manual_tests.py
Results are written to security_tests/scan/manual-results.json.
"""
import base64
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

API = "http://127.0.0.1:8000"
PW = os.environ["DAM_DEMO_PASSWORD"]
OUT = Path(__file__).parent / "scan"
OUT.mkdir(exist_ok=True)
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
results = []


def req(method, path, body=None, token=None, headers=None, raw=None, ctype="application/json"):
    h = {"Content-Type": ctype, **(headers or {})}
    if token:
        h["Authorization"] = f"Bearer {token}"
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    r = urllib.request.Request(API + path, method=method, data=data, headers=h)
    try:
        with opener.open(r, timeout=30) as resp:
            return resp.status, dict(resp.headers), resp.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()


def login(user):
    s, _, b = req("POST", "/api/token/", {"username": user, "password": PW})
    assert s == 200, (user, s, b)
    return json.loads(b)


def multipart(fields, filename, content, ctype):
    boundary = "----manualtest"
    parts = b""
    for k, v in fields.items():
        parts += f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode()
    parts += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{filename}\"\r\n"
              f"Content-Type: {ctype}\r\n\r\n").encode() + content + f"\r\n--{boundary}--\r\n".encode()
    return parts, f"multipart/form-data; boundary={boundary}"


def record(tid, owasp, title, expected, status, evidence, owner, passed):
    results.append({"id": tid, "owasp": owasp, "title": title, "expected": expected,
                    "result": "PASS" if passed else "FAIL", "status": status,
                    "evidence": evidence[:300], "owner": owner})
    print(f"{tid:4} {'PASS' if passed else 'FAIL'} [{status}] {title}")


def b64(d):
    return base64.urlsafe_b64encode(json.dumps(d, separators=(",", ":")).encode()).rstrip(b"=").decode()


def main():
    admin = login("admin_demo")["access"]
    editor = login("editor_demo")["access"]
    editor2 = login("editor2_demo")["access"]
    viewer = login("viewer_demo")["access"]
    roleadmin = login("roleadmin_demo")["access"]
    me_editor = json.loads(req("GET", "/api/me/", token=editor)[2])

    # Fixtures: an admin-owned asset and a pending version
    body, ct = multipart({"title": "Admin asset", "description": "owned by admin"}, "brand.png",
                         b"\x89PNG\r\n\x1a\n" + b"0" * 64, "image/png")
    s, _, b = req("POST", "/api/assets/", token=admin, raw=body, ctype=ct)
    asset = json.loads(b)
    aid = asset["id"]
    body, ct = multipart({"title": "v2"}, "brand2.png", b"\x89PNG\r\n\x1a\n" + b"1" * 64, "image/png")
    s, _, b = req("POST", f"/api/assets/{aid}/request_update/", token=editor2, raw=body, ctype=ct)
    vid = json.loads(b)["id"]

    # ---------------- A01 Broken Access Control ----------------
    s, _, b = req("GET", "/api/assets/")
    record("M01", "A01", "Anonymous user lists assets", "401", s, b.decode()[:120], "Ruth/Ashwin", s == 401)

    s, _, b = req("GET", f"/api/assets/{aid}/")
    record("M02", "A01", "Anonymous user reads asset detail", "401", s, b.decode()[:120], "Ruth/Ashwin", s == 401)

    file_path = asset["file"].split("8000")[-1] if "8000" in asset["file"] else asset["file"]
    s, _, b = req("GET", file_path)
    record("M03", "A01", "Anonymous user downloads stored file via /media/", "401/403", s,
           f"GET {file_path} -> {len(b)} bytes", "Ai Ling/Jiae", s in (401, 403))

    s, _, b = req("PUT", f"/api/versions/{vid}/", {"status": "approved", "version": 2, "asset": aid}, token=viewer)
    record("M04", "A01", "Viewer approves a version via PUT (bypasses admin-only PATCH)", "403", s,
           b.decode()[:160], "Ruth", s == 403)

    s, _, b = req("DELETE", f"/api/versions/{vid}/", token=viewer)
    record("M05", "A01", "Viewer deletes another user's asset version", "403", s, b.decode()[:120], "Ruth", s == 403)

    s, _, b = req("PATCH", f"/api/assets/{aid}/", {"title": "Defaced by editor"}, token=editor)
    record("M06", "A01", "Editor edits an asset owned by admin (IDOR / horizontal)", "403", s,
           b.decode()[:120], "Ruth", s == 403)

    tag = json.loads(req("POST", "/api/tags/", {"name": f"t{int(time.time())}"}, token=admin)[2])
    s, _, b = req("DELETE", f"/api/tags/{tag['id']}/", token=viewer)
    record("M07", "A01", "Viewer deletes a tag", "403", s, b.decode()[:120], "Ruth", s == 403)

    s, _, b = req("PATCH", f"/api/users/{me_editor['id']}/", {"role": "admin"}, token=editor)
    record("M08", "A01", "Editor promotes own role to admin (vertical escalation)", "403", s,
           b.decode()[:120], "Ruth", s == 403)

    s, _, b = req("GET", "/api/users/", token=roleadmin)
    record("M09", "A01", "role=admin user without is_staff manages users (role model consistency)", "200", s,
           b.decode()[:120], "Ruth", s == 200)

    s, _, b = req("GET", "/api/audit/events/", token=viewer)
    record("M10", "A01", "Viewer reads security audit log", "403", s, b.decode()[:120], "Yu Sheng", s == 403)

    s, _, b = req("GET", "/api/users/", token=viewer)
    record("M11", "A01", "Viewer lists all users (PII exposure)", "403", s, b.decode()[:80], "Ruth", s == 403)

    # ---------------- A02 / A07 JWT handling ----------------
    header, payload, sig = viewer.split(".")
    claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    claims["role"] = "admin"
    claims["user_id"] = str(json.loads(req("GET", "/api/me/", token=admin)[2])["id"])
    forged = f"{header}.{b64(claims)}.{sig}"
    s, _, b = req("GET", "/api/users/", token=forged)
    record("M12", "A02", "Tampered JWT payload (role/user_id changed, old signature)", "401", s,
           b.decode()[:120], "Ashwin", s == 401)

    none_tok = f"{b64({'alg': 'none', 'typ': 'JWT'})}.{b64(claims)}."
    s, _, b = req("GET", "/api/users/", token=none_tok)
    record("M13", "A02", "JWT with alg=none", "401", s, b.decode()[:120], "Ashwin", s == 401)

    # ---------------- A03 Injection ----------------
    s, _, b = req("GET", "/api/assets/?search=%27%20OR%201%3D1--", token=admin)
    ok = s == 200 and b"Traceback" not in b and b"syntax" not in b.lower()
    record("M14", "A03", "SQL injection payload in search parameter", "200, no SQL error, no extra rows", s,
           b.decode()[:120], "Ai Ling", ok)

    s, _, b = req("GET", "/api/assets/?ordering=title%3BDROP%20TABLE%20assets_asset", token=admin)
    record("M15", "A03", "SQL injection in ordering parameter", "ignored/400, no SQL error", s,
           b.decode()[:100], "Ai Ling", s in (200, 400) and b"Traceback" not in b)

    s, _, b = req("POST", "/api/categories/", {"name": "<script>alert('xss')</script>"}, token=admin)
    stored = b"<script>" in b
    record("M16", "A03", "Stored XSS payload in category name", "rejected or encoded", s,
           b.decode()[:120], "Ai Ling", not stored)

    body, ct = multipart({"title": "evil"}, "evil.html", b"<html><script>alert(document.cookie)</script></html>",
                         "text/html")
    s, _, b = req("POST", "/api/assets/", token=admin, raw=body, ctype=ct)
    served_type = ""
    if s == 201:
        p = json.loads(b)["file"]
        p = p.split("8000")[-1] if "8000" in p else p
        _, h, _ = req("GET", p)
        served_type = h.get("Content-Type", "")
    record("M17", "A03", "Upload HTML file with script (stored XSS via /media/)", "rejected (400)", s,
           f"served as {served_type}", "Ai Ling", s == 400)

    body, ct = multipart({"title": "trav"}, "../../evil.png", b"\x89PNG\r\n\x1a\n", "image/png")
    s, _, b = req("POST", "/api/assets/", token=admin, raw=body, ctype=ct)
    stored_name = json.loads(b).get("file", "") if s == 201 else ""
    record("M18", "A01", "Path traversal in upload filename", "name sanitised", s, stored_name,
           "Ai Ling", ".." not in stored_name)

    # ---------------- A05 Security Misconfiguration ----------------
    s, h, b = req("GET", "/api/does-not-exist/")
    record("M19", "A05", "Unknown URL reveals debug page / URL patterns", "generic 404", s,
           "debug page shown" if b"URLconf" in b or b"DEBUG = True" in b else "generic", "Jiae",
           b"URLconf" not in b and b"DEBUG = True" not in b)

    s, h, b = req("GET", "/api/assets/", token=admin)
    want = ["X-Content-Type-Options", "X-Frame-Options", "Strict-Transport-Security", "Content-Security-Policy",
            "Referrer-Policy"]
    missing = [x for x in want if x not in h]
    record("M20", "A05", "Security response headers present", "all present", s,
           f"missing: {missing}", "Jiae", not missing)

    s, h, b = req("GET", "/api/assets/", token=admin, headers={"Origin": "https://evil.example"})
    acao = h.get("Access-Control-Allow-Origin")
    record("M21", "A05", "CORS allows untrusted origin", "no ACAO for evil origin", s, f"ACAO={acao}", "Jiae",
           acao is None)

    s, h, b = req("GET", "/api/assets/")
    record("M22", "A02", "Transport encryption (HTTPS) on API", "HTTPS only", s, "served over plain HTTP", "Jiae",
           API.startswith("https"))

    # ---------------- A07 Identification & Authentication ----------------
    codes = [req("POST", "/api/token/", {"username": "viewer_demo", "password": f"guess{i}"})[0] for i in range(20)]
    record("M23", "A07", "Brute force: 20 wrong passwords in a row", "429 / lockout before 20", codes[-1],
           f"codes={sorted(set(codes))}", "Ashwin", 429 in codes)

    s1, _, b1 = req("POST", "/api/token/", {"username": "viewer_demo", "password": "wrong"})
    s2, _, b2 = req("POST", "/api/token/", {"username": "no_such_user_x", "password": "wrong"})
    record("M24", "A07", "Account enumeration via login response", "identical response", s1,
           f"same={b1 == b2 and s1 == s2}", "Ashwin", b1 == b2 and s1 == s2)

    s, _, b = req("POST", "/api/users/", {"username": f"weak{int(time.time())}", "password": "123", "role": "viewer"},
                  token=admin)
    record("M25", "A07", "Weak password accepted on user creation", "400", s, b.decode()[:120], "Ashwin", s == 400)

    refresh = login("viewer_demo")["refresh"]
    s, _, b = req("POST", "/api/logout/", {"refresh": refresh}, token=viewer)
    s2, _, _ = req("POST", "/api/token/refresh/", {"refresh": refresh})
    record("M26", "A07", "Logout revokes refresh token", "logout 2xx, refresh then 401", s,
           f"logout={s}, refresh-after={s2}", "Ashwin", s in (200, 205) and s2 == 401)

    # ---------------- A09 Logging & Monitoring (own module) ----------------
    summary = json.loads(req("GET", "/api/audit/summary/", token=admin)[2])
    alerts = {a["event_type"] for a in summary["recent_alerts"]}
    record("M27", "A09", "Brute force (M23) detected and alerted", "BRUTE_FORCE_SUSPECTED", 200,
           f"alerts={sorted(alerts)}", "Yu Sheng", "BRUTE_FORCE_SUSPECTED" in alerts)
    ev = json.loads(req("GET", "/api/audit/events/?event_type=ACCESS_DENIED", token=admin)[2])
    record("M28", "A09", "Denied requests (M04-M11) recorded with user and IP", ">0 ACCESS_DENIED", 200,
           f"count={ev['count']}", "Yu Sheng", ev["count"] > 0)
    integ = json.loads(req("GET", "/api/audit/integrity/", token=admin)[2])
    record("M29", "A09", "Audit chain intact after attack traffic", "intact", 200, json.dumps(integ), "Yu Sheng",
           integ["intact"])

    (OUT / "manual-results.json").write_text(json.dumps(results, indent=1))
    fails = [r for r in results if r["result"] == "FAIL"]
    print(f"\n{len(results)} cases, {len(fails)} FAIL (vulnerability confirmed)")


if __name__ == "__main__":
    main()
