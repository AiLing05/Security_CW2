"""Baseline OWASP ZAP scan of the local DAM app (authorised, localhost only).

Phase A: unauthenticated spider + passive + active scan of the backend API,
         spider + passive scan of the Next.js frontend.
Phase B: same backend scan authenticated as admin (Bearer token injected by
         a ZAP replacer rule, refreshed every 4 minutes).

Run (ZAP daemon on :8090, backend on :8000, frontend on :3000):
    set ZAP_API_KEY=<zap key>  and  DAM_DEMO_PASSWORD=<demo admin password>
    python security_tests/zap_scan.py
Results are written to security_tests/scan/.
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path

HERE = Path(__file__).parent
OUT = HERE / "scan"
OUT.mkdir(exist_ok=True)
KEY = os.environ["ZAP_API_KEY"]
ZAP = "http://127.0.0.1:8090"
API = "http://127.0.0.1:8000"
FRONT = "http://localhost:3000"
PW = os.environ["DAM_DEMO_PASSWORD"]

direct = urllib.request.build_opener(urllib.request.ProxyHandler({}))
proxied = urllib.request.build_opener(urllib.request.ProxyHandler({"http": ZAP}))


def zap(path, **params):
    params["apikey"] = KEY
    url = f"{ZAP}{path}?{urllib.parse.urlencode(params)}"
    with direct.open(url, timeout=120) as r:
        body = r.read()
    return json.loads(body) if path.startswith("/JSON") else body


def http(opener, method, url, body=None, token=None, ctype="application/json"):
    headers = {"Content-Type": ctype}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if isinstance(body, dict) else body
    req = urllib.request.Request(url, method=method, data=data, headers=headers)
    try:
        with opener.open(req, timeout=60) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def token(user="admin_demo"):
    s, b = http(direct, "POST", f"{API}/api/token/", {"username": user, "password": PW})
    assert s == 200, (s, b)
    return json.loads(b)["access"]


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def seed_data(tok):
    """Create a category, tag and asset so detail URLs exist."""
    http(direct, "POST", f"{API}/api/categories/", {"name": "Logos"}, tok)
    http(direct, "POST", f"{API}/api/tags/", {"name": "brand"}, tok)
    boundary = "----zapseed"
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 64
    body = (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"title\"\r\n\r\nSeed logo\r\n"
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"description\"\r\n\r\nseed\r\n"
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"seed.png\"\r\n"
        f"Content-Type: image/png\r\n\r\n"
    ).encode() + png + f"\r\n--{boundary}--\r\n".encode()
    s, b = http(direct, "POST", f"{API}/api/assets/", body, tok, f"multipart/form-data; boundary={boundary}")
    log("seed asset", s)
    return json.loads(b).get("id") if s == 201 else 1


def explore(tok, asset_id):
    urls = [
        "/api/", "/api/assets/", f"/api/assets/{asset_id}/", "/api/assets/?search=logo",
        "/api/categories/", "/api/categories/1/", "/api/tags/", "/api/tags/1/",
        "/api/users/", "/api/users/1/", "/api/versions/", f"/api/versions/?asset_id={asset_id}",
        "/api/me/", "/api/audit/events/", "/api/audit/summary/", "/api/audit/integrity/",
        "/admin/login/", "/",
    ]
    for u in urls:
        http(proxied, "GET", API + u, token=tok)
    http(proxied, "POST", f"{API}/api/token/", {"username": "zap_probe", "password": "wrong"})
    http(proxied, "POST", f"{API}/api/token/refresh/", {"refresh": "invalid"})
    http(proxied, "POST", f"{API}/api/categories/", {"name": "zap-cat"}, tok)
    http(proxied, "POST", f"{API}/api/tags/", {"name": "zap-tag"}, tok)


def wait(kind, scan_id, refresh=None):
    last = time.time()
    while True:
        status = int(zap(f"/JSON/{kind}/view/status/", scanId=scan_id)["status"])
        if status >= 100:
            return
        if refresh and time.time() - last > 240:
            refresh()
            last = time.time()
        log(f"{kind} {status}%")
        time.sleep(15)


def wait_passive():
    while int(zap("/JSON/pscan/view/recordsToScan/")["recordsToScan"]) > 0:
        time.sleep(3)


def set_auth_header(tok):
    try:
        zap("/JSON/replacer/action/removeRule/", description="auth")
    except urllib.error.HTTPError:
        pass
    zap("/JSON/replacer/action/addRule/", description="auth", enabled="true", matchType="REQ_HEADER",
        matchRegex="false", matchString="Authorization", replacement=f"Bearer {tok}", initiators="")


def save(label):
    (OUT / f"zap-{label}.html").write_bytes(zap("/OTHER/core/other/htmlreport/"))
    alerts = zap("/JSON/core/view/alerts/", start=0, count=5000)["alerts"]
    (OUT / f"zap-{label}-alerts.json").write_text(json.dumps(alerts, indent=1))
    summary = {}
    for a in alerts:
        k = (a["risk"], a["alert"])
        summary.setdefault(k, set()).add(a["url"].split("?")[0])
    lines = [f"{risk:13} {name}  ({len(urls)} URL)" for (risk, name), urls in
             sorted(summary.items(), key=lambda kv: ["High", "Medium", "Low", "Informational"].index(kv[0][0]))]
    (OUT / f"zap-{label}-summary.txt").write_text("\n".join(lines))
    log(f"--- {label}: {len(alerts)} alert instances\n" + "\n".join(lines))


def scan_backend(tok=None, refresh=None):
    sid = zap("/JSON/spider/action/scan/", url=f"{API}/api/", maxChildren=0, recurse="true")["scan"]
    wait("spider", sid)
    wait_passive()
    sid = zap("/JSON/ascan/action/scan/", url=API, recurse="true", inScopeOnly="false")["scan"]
    wait("ascan", sid, refresh)
    wait_passive()


def main():
    phases = sys.argv[1:] or ["A", "B"]
    zap("/JSON/ascan/action/setOptionMaxScanDurationInMins/", Integer=20)
    zap("/JSON/ascan/action/setOptionThreadPerHost/", Integer=4)
    admin_tok = token()
    asset_id = seed_data(admin_tok)

    if "A" in phases:
        log("=== Phase A: unauthenticated")
        zap("/JSON/core/action/newSession/", overwrite="true")
        explore(None, asset_id)
        sid = zap("/JSON/spider/action/scan/", url=f"{FRONT}/login", recurse="true")["scan"]
        http(proxied, "GET", f"{FRONT}/login")
        wait("spider", sid)
        scan_backend()
        save("A-unauthenticated")

    if "B" in phases:
        log("=== Phase B: authenticated as admin")
        zap("/JSON/core/action/newSession/", overwrite="true")
        set_auth_header(token())
        explore(token(), asset_id)
        scan_backend(refresh=lambda: set_auth_header(token()))
        save("B-authenticated-admin")
        zap("/JSON/replacer/action/removeRule/", description="auth")


if __name__ == "__main__":
    main()
