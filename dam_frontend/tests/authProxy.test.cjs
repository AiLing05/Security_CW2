const test = require("node:test");
const assert = require("node:assert/strict");
const http = require("node:http");
const { once } = require("node:events");
const { createHandler } = require("../lib/serverAuth.cjs");

const origin = "https://localhost:3443";
const jwt = (seconds, id) => `header.${Buffer.from(JSON.stringify({ exp: Math.floor(Date.now() / 1000) + seconds, id })).toString("base64url")}.signature`;
const access = jwt(300, "access");
const refresh = jwt(86400, "refresh");

async function fixture(t) {
  const calls = [];
  let reply = () => Response.json({ access, refresh });
  const handler = createHandler({ origin, request: async (url, options) => {
    calls.push({ url, ...options });
    return reply(url, options);
  } });
  const server = http.createServer(handler).listen(0, "127.0.0.1");
  await once(server, "listening");
  t.after(() => new Promise((resolve) => { server.closeAllConnections(); server.close(resolve); }));
  const base = `http://127.0.0.1:${server.address().port}/api/`;
  const request = (path, options = {}) => fetch(base + path, options);
  const csrf = await request("auth/csrf/");
  const token = (await csrf.json()).csrfToken;
  const csrfCookie = csrf.headers.getSetCookie()[0].split(";")[0];
  const headers = { Origin: origin, "X-CSRF-Token": token, Cookie: csrfCookie, "Content-Type": "application/json" };
  return { request, headers, calls, setReply: (fn) => { reply = fn; } };
}

test("login, refresh, logout and mutations reject missing/incorrect CSRF or foreign origins", async (t) => {
  const f = await fixture(t);
  for (const path of ["token/", "token/refresh/", "logout/", "assets/"]) {
    for (const change of [{ "X-CSRF-Token": "" }, { "X-CSRF-Token": "a".repeat(64) }, { Origin: "https://evil.example" }, { Origin: "https://localhost:8443" }, { Origin: "" }, { "Sec-Fetch-Site": "cross-site" }]) {
      const r = await f.request(path, { method: "POST", headers: { ...f.headers, ...change }, body: "{}" });
      assert.equal(r.status, 403);
    }
  }
  assert.equal(f.calls.length, 0);
});

test("login exposes no JWTs in JSON and issues host-only Secure HttpOnly Strict cookies", async (t) => {
  const f = await fixture(t);
  const r = await f.request("token/", { method: "POST", headers: f.headers, body: JSON.stringify({ username: "test", password: "private" }) });
  assert.deepEqual(await r.json(), { authenticated: true });
  assert.equal(r.headers.get("cache-control"), "no-store");
  for (const cookie of r.headers.getSetCookie()) {
    assert.match(cookie, /^__Host-dam_(access|refresh)=/);
    assert.match(cookie, /HttpOnly/);
    assert.match(cookie, /Secure/);
    assert.match(cookie, /SameSite=Strict/);
    assert.match(cookie, /Path=\//);
    assert.doesNotMatch(cookie, /Domain=/i);
  }
});

test("refresh uses only its HttpOnly cookie and replaces both rotated tokens", async (t) => {
  const f = await fixture(t);
  const nextAccess = jwt(300, "new-access"), nextRefresh = jwt(86400, "new-refresh");
  f.setReply(() => Response.json({ access: nextAccess, refresh: nextRefresh }));
  const r = await f.request("token/refresh/", { method: "POST", headers: { ...f.headers, Cookie: `${f.headers.Cookie}; __Host-dam_refresh=${refresh}` }, body: JSON.stringify({ refresh: "attacker-token" }) });
  assert.equal(r.status, 200);
  assert.equal(JSON.parse(f.calls[0].body).refresh, refresh);
  assert.deepEqual(await r.json(), { authenticated: true });
  assert.ok(r.headers.getSetCookie().some((value) => value.includes(nextRefresh)));
});

test("logout blacklists the cookie refresh token and expires both auth cookies", async (t) => {
  const f = await fixture(t);
  f.setReply(() => Response.json({ detail: "Logged out" }));
  const r = await f.request("logout/", { method: "POST", headers: { ...f.headers, Cookie: `${f.headers.Cookie}; __Host-dam_access=${access}; __Host-dam_refresh=${refresh}` } });
  assert.equal(r.status, 200);
  assert.equal(f.calls[0].headers.Authorization, `Bearer ${access}`);
  assert.equal(JSON.parse(f.calls[0].body).refresh, refresh);
  assert.equal(r.headers.getSetCookie().length, 2);
  assert.ok(r.headers.getSetCookie().every((cookie) => cookie.includes("Max-Age=0")));
});

test("rejected refresh clears cookies without returning backend tokens", async (t) => {
  const f = await fixture(t);
  f.setReply(() => Response.json({ detail: "Revoked", access: "must-not-leak" }, { status: 401 }));
  const r = await f.request("token/refresh/", { method: "POST", headers: { ...f.headers, Cookie: `${f.headers.Cookie}; __Host-dam_refresh=${refresh}` } });
  assert.equal(r.status, 401);
  assert.deepEqual(await r.json(), { detail: "Revoked" });
  assert.ok(r.headers.getSetCookie().every((cookie) => cookie.includes("Max-Age=0")));
});

test("file retrieval streams bytes and ignores browser-supplied Bearer credentials", async (t) => {
  const f = await fixture(t);
  const bytes = Buffer.from([0, 255, 12, 3]);
  f.setReply(() => new Response(bytes, { headers: { "Content-Type": "image/png" } }));
  const r = await f.request("assets/1/file/", { headers: { Cookie: `__Host-dam_access=${access}`, Authorization: "Bearer injected" } });
  assert.deepEqual(Buffer.from(await r.arrayBuffer()), bytes);
  assert.equal(f.calls[0].headers.Authorization, `Bearer ${access}`);
  assert.equal(r.headers.get("Content-Type"), "image/png");
});

test("authenticated multipart uploads preserve content type, body and search parameters", async (t) => {
  const f = await fixture(t);
  f.setReply(() => Response.json({ id: 1 }, { status: 201 }));
  const body = "--boundary\r\nContent-Disposition: form-data; name=title\r\n\r\nImage\r\n--boundary--";
  const r = await f.request("assets/?page=2", { method: "POST", headers: { ...f.headers, "Content-Type": "multipart/form-data; boundary=boundary" }, body });
  assert.equal(r.status, 201);
  assert.equal(f.calls[0].body.toString(), body);
  assert.equal(f.calls[0].headers["Content-Type"], "multipart/form-data; boundary=boundary");
  assert.match(f.calls[0].url, /assets\/\?page=2$/);
});

test("duplicate auth cookies, unknown paths and GET auth requests fail closed", async (t) => {
  const f = await fixture(t);
  assert.equal((await f.request("me/", { headers: { Cookie: "__Host-dam_access=one; __Host-dam_access=two" } })).status, 400);
  assert.equal((await f.request("admin/")).status, 404);
  assert.equal((await f.request("token/")).status, 405);
  assert.equal(f.calls.length, 0);
});

test("configuration rejects remote plaintext and credentials in the upstream URL", () => {
  assert.throws(() => createHandler({ upstream: "http://remote.example/api" }));
  assert.throws(() => createHandler({ upstream: "https://user:password@example.com/api" }));
});
