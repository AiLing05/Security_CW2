const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const moduleFrom = (name) => import("data:text/javascript;base64," + Buffer.from(fs.readFileSync(path.join(__dirname, "../lib", name), "utf8") + `\n// ${Math.random()}`).toString("base64"));

test("session initialization removes all legacy stored credentials and keeps only profile metadata", async (t) => {
  global.window = {};
  const store = new Map([["access_token", "old-access"], ["refresh_token", "old-refresh"], ["user", '{"access":"old-access"}']]);
  global.localStorage = { removeItem: (key) => store.delete(key), setItem: (key, value) => store.set(key, value) };
  t.after(() => { delete global.window; delete global.localStorage; });
  const session = await moduleFrom("browserSession.js");
  session.setSessionUser({ username: "alice", role: "viewer" });
  assert.deepEqual([...store.keys()].sort(), ["role", "username"]);
  assert.equal(session.isAuthenticated(), true);
  session.setSessionUser(null);
  assert.equal(session.isAuthenticated(), false);
  assert.equal(store.size, 0);
});

test("API requests stay same-origin, attach CSRF, discard Bearer headers and share one refresh", async (t) => {
  global.window = { location: { origin: "https://localhost:3443" } };
  const originalFetch = global.fetch;
  t.after(() => { global.fetch = originalFetch; delete global.window; });
  const calls = [];
  let refreshed = false;
  global.fetch = async (url, options) => {
    calls.push({ url, options });
    if (String(url).includes("auth/csrf")) return Response.json({ csrfToken: "csrf-test" });
    if (String(url).includes("token/refresh")) {
      await new Promise((resolve) => setTimeout(resolve, 15));
      refreshed = true;
      return Response.json({ authenticated: true });
    }
    return Response.json({}, { status: refreshed ? 200 : 401 });
  };
  const { apiFetch } = await moduleFrom("apiFetch.js");
  const responses = await Promise.all([apiFetch("/api/assets/"), apiFetch("/api/me/")]);
  assert.ok(responses.every((response) => response.ok));
  assert.equal(calls.filter((call) => String(call.url).includes("token/refresh")).length, 1);
  await apiFetch("/api/assets/", { method: "POST", headers: { Authorization: "Bearer old" }, body: "{}" });
  const options = calls.at(-1).options;
  assert.equal(options.headers.get("X-CSRF-Token"), "csrf-test");
  assert.equal(options.headers.has("Authorization"), false);
  assert.equal(options.credentials, "same-origin");
  await assert.rejects(apiFetch("https://evil.example/api/assets/"));
});

test("an expired CSRF cookie is recovered once; permission errors are not retried", async (t) => {
  global.window = { location: { origin: "https://localhost:3443" } };
  const originalFetch = global.fetch;
  t.after(() => { global.fetch = originalFetch; delete global.window; });
  let csrfRequests = 0, mutations = 0;
  global.fetch = async (url) => {
    if (String(url).includes("auth/csrf")) return Response.json({ csrfToken: `token-${++csrfRequests}` });
    mutations++;
    if (mutations === 1) return Response.json({ code: "csrf_failed" }, { status: 403 });
    return Response.json({ detail: "Not permitted" }, { status: 403 });
  };
  const { apiFetch } = await moduleFrom("apiFetch.js");
  const response = await apiFetch("/api/categories/", { method: "POST", body: "{}" });
  assert.equal(response.status, 403);
  assert.equal(csrfRequests, 2);
  assert.equal(mutations, 2);
});
