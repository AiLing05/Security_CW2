
import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const source = await readFile(
  new URL("../lib/tokenManager.js", import.meta.url),
  "utf8"
);

// Load the existing module without changing project configuration.
const moduleUrl =
  `data:text/javascript;base64,${Buffer.from(source).toString("base64")}`;

function setupStorage(values = {}) {
  const storage = new Map(Object.entries(values));

  globalThis.window = {};
  globalThis.localStorage = {
    getItem: (key) => storage.get(key) ?? null,
    setItem: (key, value) => storage.set(key, String(value)),
    removeItem: (key) => storage.delete(key),
  };

  return storage;
}

async function loadTokenManager() {
  // A fresh module instance resets its shared refreshPromise.
  return import(`${moduleUrl}#${Date.now()}-${Math.random()}`);
}

test("successful refresh saves rotated tokens", async () => {
  const storage = setupStorage({
    access_token: "old-access",
    refresh_token: "old-refresh",
  });

  globalThis.fetch = async () => ({
    ok: true,
    status: 200,
    json: async () => ({
      access: "new-access",
      refresh: "new-refresh",
    }),
  });

  const { refreshAccessToken } = await loadTokenManager();
  const access = await refreshAccessToken();

  assert.equal(access, "new-access");
  assert.equal(storage.get("access_token"), "new-access");
  assert.equal(storage.get("refresh_token"), "new-refresh");
});

test("401 clears rejected session tokens", async () => {
  const storage = setupStorage({
    access_token: "old-access",
    refresh_token: "old-refresh",
  });

  globalThis.fetch = async () => ({
    ok: false,
    status: 401,
  });

  const { refreshAccessToken } = await loadTokenManager();

  await assert.rejects(
    refreshAccessToken(),
    /Refresh token rejected/
  );

  assert.equal(storage.has("access_token"), false);
  assert.equal(storage.has("refresh_token"), false);
});

test("500 preserves existing tokens", async () => {
  const storage = setupStorage({
    access_token: "old-access",
    refresh_token: "old-refresh",
  });

  globalThis.fetch = async () => ({
    ok: false,
    status: 500,
  });

  const { refreshAccessToken } = await loadTokenManager();

  await assert.rejects(
    refreshAccessToken(),
    /Token refresh failed: HTTP 500/
  );

  assert.equal(storage.get("access_token"), "old-access");
  assert.equal(storage.get("refresh_token"), "old-refresh");
});

test("network failure preserves existing tokens", async () => {
  const storage = setupStorage({
    access_token: "old-access",
    refresh_token: "old-refresh",
  });

  globalThis.fetch = async () => {
    throw new Error("Network unavailable");
  };

  const { refreshAccessToken } = await loadTokenManager();

  await assert.rejects(
    refreshAccessToken(),
    /Network unavailable/
  );

  assert.equal(storage.get("access_token"), "old-access");
  assert.equal(storage.get("refresh_token"), "old-refresh");
});

test("logout during refresh cannot restore old tokens", async () => {
  const storage = setupStorage({
    access_token: "old-access",
    refresh_token: "old-refresh",
  });

  let finishRequest;

  globalThis.fetch = () =>
    new Promise((resolve) => {
      finishRequest = resolve;
    });

  const { refreshAccessToken, clearAuthTokens } =
    await loadTokenManager();

  const pending = refreshAccessToken();

  clearAuthTokens();

  finishRequest({
    ok: true,
    status: 200,
    json: async () => ({
      access: "new-access",
      refresh: "new-refresh",
    }),
  });

  await assert.rejects(
    pending,
    /Authentication session changed/
  );

  assert.equal(storage.has("access_token"), false);
  assert.equal(storage.has("refresh_token"), false);
});

test("concurrent refresh calls share one request", async () => {
  setupStorage({
    access_token: "old-access",
    refresh_token: "old-refresh",
  });

  let requestCount = 0;

  globalThis.fetch = async () => {
    requestCount++;

    return {
      ok: true,
      status: 200,
      json: async () => ({
        access: "new-access",
        refresh: "new-refresh",
      }),
    };
  };

  const { refreshAccessToken } = await loadTokenManager();

  const results = await Promise.all([
    refreshAccessToken(),
    refreshAccessToken(),
    refreshAccessToken(),
  ]);

  assert.deepEqual(results, [
    "new-access",
    "new-access",
    "new-access",
  ]);

  assert.equal(requestCount, 1);
});

test("rejected old refresh cannot clear a newer login", async () => {
  const storage = setupStorage({
    access_token: "session-A-access",
    refresh_token: "session-A-refresh",
  });

  let finishRequest;

  globalThis.fetch = () =>
    new Promise((resolve) => {
      finishRequest = resolve;
    });

  const { refreshAccessToken } = await loadTokenManager();

  // Session A starts refreshing.
  const pending = refreshAccessToken();

  // Session B logs in before Session A's response arrives.
  storage.set("access_token", "session-B-access");
  storage.set("refresh_token", "session-B-refresh");

  // Session A's refresh token is rejected.
  finishRequest({
    ok: false,
    status: 401,
  });

  await assert.rejects(
    pending,
    /Refresh token rejected/
  );

  // Session B must remain authenticated.
  assert.equal(
    storage.get("access_token"),
    "session-B-access"
  );

  assert.equal(
    storage.get("refresh_token"),
    "session-B-refresh"
  );
});


test("new session refresh does not reuse old session refresh", async () => {
  const storage = setupStorage({
    access_token: "session-A-access",
    refresh_token: "session-A-refresh",
  });

  const requests = [];

  globalThis.fetch = (url, options) =>
    new Promise((resolve) => {
      requests.push({
        refresh: JSON.parse(options.body).refresh,
        resolve,
      });
    });

  const { refreshAccessToken } = await loadTokenManager();

  // Session A starts a refresh request.
  const oldRefresh = refreshAccessToken();

  assert.equal(requests.length, 1);
  assert.equal(requests[0].refresh, "session-A-refresh");

  // Session B logs in while Session A's request is pending.
  storage.set("access_token", "session-B-access");
  storage.set("refresh_token", "session-B-refresh");

  // Session B must start a separate refresh request.
  const newRefresh = refreshAccessToken();

  assert.equal(requests.length, 2);
  assert.equal(requests[1].refresh, "session-B-refresh");

  // Complete Session B's refresh successfully.
  requests[1].resolve({
    ok: true,
    status: 200,
    json: async () => ({
      access: "session-B-new-access",
      refresh: "session-B-new-refresh",
    }),
  });

  assert.equal(await newRefresh, "session-B-new-access");

  // Session A's old response arrives afterwards.
  requests[0].resolve({
    ok: true,
    status: 200,
    json: async () => ({
      access: "session-A-new-access",
      refresh: "session-A-new-refresh",
    }),
  });

  await assert.rejects(
    oldRefresh,
    /Authentication session changed during refresh/
  );

  // Session A must not overwrite Session B's credentials.
  assert.equal(
    storage.get("access_token"),
    "session-B-new-access"
  );

  assert.equal(
    storage.get("refresh_token"),
    "session-B-new-refresh"
  );
});
