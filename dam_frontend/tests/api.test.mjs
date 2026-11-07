import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const source = await readFile(new URL("../lib/apiFetch.js", import.meta.url), "utf8");
async function load(t, request) {
  const oldFetch = globalThis.fetch;
  const events = [];
  globalThis.window = { location: { origin: "https://localhost:3443" }, dispatchEvent: (event) => events.push(event.type) };
  globalThis.fetch = (url, options) => String(url).includes("auth/csrf") ? Promise.resolve(Response.json({ csrfToken: "csrf" })) : request(String(url), options);
  t.after(() => { globalThis.fetch = oldFetch; delete globalThis.window; });
  const api = await import(`data:text/javascript;base64,${Buffer.from(source).toString("base64")}#${Math.random()}`);
  return { ...api, events };
}

test("rejected cookie refresh expires the current UI session", async (t) => {
  const api = await load(t, async () => Response.json({}, { status: 401 }));
  assert.equal((await api.apiFetch("/api/assets/")).status, 401);
  assert.deepEqual(api.events, ["dam:session-expired"]);
});

test("temporary refresh failure does not expire the session", async (t) => {
  const api = await load(t, async (url) => Response.json({}, { status: url.includes("token/refresh") ? 500 : 401 }));
  await assert.rejects(api.apiFetch("/api/assets/"), /HTTP 500/);
  assert.deepEqual(api.events, []);
});

test("network refresh failure preserves the session", async (t) => {
  const api = await load(t, async (url) => {
    if (url.includes("token/refresh")) throw new Error("Network unavailable");
    return Response.json({}, { status: 401 });
  });
  await assert.rejects(api.apiFetch("/api/assets/"), /Network unavailable/);
  assert.deepEqual(api.events, []);
});

test("successful refresh retries once and a second 401 cannot loop", async (t) => {
  let refreshes = 0, protectedCalls = 0;
  const api = await load(t, async (url) => {
    if (url.includes("token/refresh")) { refreshes++; return Response.json({ authenticated: true }); }
    protectedCalls++;
    return Response.json({}, { status: 401 });
  });
  assert.equal((await api.apiFetch("/api/assets/")).status, 401);
  assert.equal(refreshes, 1);
  assert.equal(protectedCalls, 2);
});

test("new login aborts an old refresh and old rejection cannot expire the new session", async (t) => {
  let began;
  const started = new Promise(resolve => { began = resolve; });
  const api = await load(t, async (url, options) => {
    if (url.includes("token/refresh")) return new Promise((resolve, reject) => {
      began();
      options.signal.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")), { once: true });
    });
    return Response.json({}, { status: url.includes("/token/") ? 200 : 401 });
  });
  const old = api.apiFetch("/api/assets/").catch(error => error);
  await started;
  assert.equal((await api.apiFetch("/api/token/", { method: "POST", body: "{}" })).status, 200);
  assert.equal((await old).name, "AbortError");
  assert.deepEqual(api.events, []);
});

test("a new session gets its own refresh rather than sharing an older one", async (t) => {
  let began, refreshes = 0, valid = false;
  const started = new Promise(resolve => { began = resolve; });
  const api = await load(t, async (url, options) => {
    if (url.includes("token/refresh")) {
      refreshes++;
      if (refreshes === 1) return new Promise((resolve, reject) => {
        began();
        options.signal.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")), { once: true });
      });
      valid = true;
      return Response.json({ authenticated: true });
    }
    return Response.json({}, { status: url.includes("/token/") || valid ? 200 : 401 });
  });
  const old = api.apiFetch("/api/assets/").catch(error => error);
  await started;
  await api.apiFetch("/api/token/", { method: "POST", body: "{}" });
  await old;
  assert.equal((await api.apiFetch("/api/assets/")).status, 200);
  assert.equal(refreshes, 2);
});

test("logout waits for rotation before asking the server to revoke the refresh cookie", async (t) => {
  let began, finish;
  const started = new Promise(resolve => { began = resolve; });
  const order = [];
  const api = await load(t, async (url) => {
    if (url.includes("token/refresh")) { began(); await new Promise(resolve => { finish = resolve; }); order.push("rotated"); return Response.json({ authenticated: true }); }
    if (url.includes("logout")) { order.push("logout"); return Response.json({}); }
    return Response.json({}, { status: 401 });
  });
  const old = api.apiFetch("/api/assets/").catch(error => error);
  await started;
  const logout = api.apiFetch("/api/logout/", { method: "POST" });
  finish();
  await logout;
  await old;
  assert.deepEqual(order, ["rotated", "logout"]);
});
