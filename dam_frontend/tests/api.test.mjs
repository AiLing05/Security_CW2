import test from "node:test";
import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
import vm from "node:vm";

const source = await readFile(
    new URL("../lib/api.js", import.meta.url),
    "utf8"
);

// Replace only the three imports with test-controlled dependencies.
const testSource = source
    .replace(/^import .*from "\.\/tokenManager";\s*/m, "")
    .replace(/^import .*from "\.\.\/redux\/store";\s*/m, "")
    .replace(/^import .*from "\.\.\/redux\/userSlice";\s*/m, "")
    .replace(/^export /gm, "");

function setupApi({
                      refreshError,
                      controlledRefresh = false,
                      retryStatus = 200,
                      onRefreshRejected,
                  } = {}) {
    const storage = new Map([
        ["access_token", "expired-access"],
        ["refresh_token", "expired-refresh"],
        ["user", '{"username":"testuser","role":"user"}'],
        ["username", "testuser"],
        ["role", "user"],
    ]);

    const localStorage = {
        getItem: (key) => storage.get(key) ?? null,
        removeItem: (key) => storage.delete(key),
    };

    const redirects = [];
    const dispatched = [];

    const window = {
        location: {
            pathname: "/assets",
            replace: (path) => redirects.push(path),
        },
    };

    const store = {
        dispatch(action) {
            dispatched.push(action);

            // Simulate the existing Redux logout reducer's storage cleanup.
            if (action.type === "user/logout") {
                for (const key of [
                    "user",
                    "access_token",
                    "refresh_token",
                    "role",
                    "username",
                ]) {
                    localStorage.removeItem(key);
                }
            }
        },
    };

    const logout = () => ({type: "user/logout"});

    const getAccessToken = () =>
        localStorage.getItem("access_token");


    let finishRefresh;

    const refreshAccessToken = async () => {
        // Capture the token belonging to the refresh request.
        const originalRefresh = localStorage.getItem("refresh_token");

        if (controlledRefresh) {
            await new Promise((resolve) => {
                finishRefresh = resolve;
            });
        }

        if (refreshError) {
            // Match tokenManager.js: never clear a newer session.
            if (
                refreshError.message === "Refresh token rejected." &&
                localStorage.getItem("refresh_token") === originalRefresh
            ) {
                localStorage.removeItem("access_token");
                localStorage.removeItem("refresh_token");

                // Test-only hook: simulate a new login after cleanup.
                if (onRefreshRejected) {
                    onRefreshRejected(storage);
                }
            }

            throw refreshError;
        }

        return "new-access";
    };


    const requests = [];

    const fetch = async (url, options) => {
        requests.push({url, options});

        if (requests.length === 1) {
            return {ok: false, status: 401};
        }

        return {
            ok: retryStatus >= 200 && retryStatus < 300,
            status: retryStatus,
            json: async () => ({results: []}),
        };
    };

    const context = vm.createContext({
        fetch,
        window,
        localStorage,
        store,
        logout,
        getAccessToken,
        refreshAccessToken,
        process,
    });

    vm.runInContext(
        `${testSource}
     globalThis.testApi = { fetchWithToken };`,
        context
    );

    return {
        fetchWithToken: context.testApi.fetchWithToken,
        storage,
        redirects,
        dispatched,
        requests,
        finishRefresh: () => finishRefresh(),
    };
}

test("rejected refresh logs out and redirects to login", async () => {
    const app = setupApi({
        refreshError: new Error("Refresh token rejected."),
    });

    await assert.rejects(
        app.fetchWithToken("/assets/", "expired-access"),
        /Refresh token rejected/
    );

    assert.equal(app.dispatched.length, 1);
    assert.equal(app.dispatched[0].type, "user/logout");
    assert.deepEqual(app.redirects, ["/login"]);

    for (const key of [
        "access_token",
        "refresh_token",
        "user",
        "username",
        "role",
    ]) {
        assert.equal(app.storage.has(key), false);
    }
});

test("temporary refresh failure does not log out user", async () => {
    const app = setupApi({
        refreshError: new Error("Token refresh failed: HTTP 500"),
    });

    await assert.rejects(
        app.fetchWithToken("/assets/", "expired-access"),
        /HTTP 500/
    );

    assert.equal(app.dispatched.length, 0);
    assert.equal(app.redirects.length, 0);
    assert.equal(app.storage.get("refresh_token"), "expired-refresh");
});

test("successful refresh retries the protected request", async () => {
    const app = setupApi();

    const result = await app.fetchWithToken(
        "/assets/",
        "expired-access"
    );

    assert.deepEqual(result.results, []);
    assert.equal(app.requests.length, 2);
    assert.equal(
        app.requests[1].options.headers.Authorization,
        "Bearer new-access"
    );
    assert.equal(app.dispatched.length, 0);
    assert.equal(app.redirects.length, 0);
});


test("old refresh rejection must not log out a newer session", async () => {
    const app = setupApi({
        refreshError: new Error("Refresh token rejected."),
        controlledRefresh: true,
    });

    // Session A starts an authenticated API request.
    const pending = app.fetchWithToken(
        "/assets/",
        "expired-access"
    );

    // Allow the initial 401 to trigger the pending refresh.
    await new Promise((resolve) => setImmediate(resolve));

    // Session B logs in while Session A's refresh is pending.
    app.storage.set("access_token", "session-B-access");
    app.storage.set("refresh_token", "session-B-refresh");

    // Session A's refresh request now returns 401.
    app.finishRefresh();

    await assert.rejects(
        pending,
        /Refresh token rejected/
    );

    // Session B must remain authenticated.
    assert.equal(app.dispatched.length, 0);
    assert.equal(app.redirects.length, 0);

    assert.equal(
        app.storage.get("access_token"),
        "session-B-access"
    );

    assert.equal(
        app.storage.get("refresh_token"),
        "session-B-refresh"
    );
});

test("second 401 is not retried indefinitely", async () => {
    const app = setupApi({retryStatus: 401});

    await assert.rejects(
        app.fetchWithToken("/assets/", "expired-access"),
        (error) => error.status === 401
    );

    // One original request and one retry only.
    assert.equal(app.requests.length, 2);

    // No repeated refresh/retry loop.
    assert.equal(app.redirects.length, 0);
});



test("new login after token cleanup must not be logged out", async () => {
    const app = setupApi({
        refreshError: new Error("Refresh token rejected."),

        onRefreshRejected: (storage) => {
            // Session A's tokens have just been cleared.
            // Simulate Session B logging in before API error handling.
            storage.set("access_token", "session-B-access");
            storage.set("refresh_token", "session-B-refresh");
            storage.set("username", "session-B");
        },
    });

    await assert.rejects(
        app.fetchWithToken("/assets/", "expired-access"),
        /Refresh token rejected/
    );

    // Session B must not be logged out.
    assert.equal(app.dispatched.length, 0);
    assert.equal(app.redirects.length, 0);

    assert.equal(
        app.storage.get("access_token"),
        "session-B-access"
    );

    assert.equal(
        app.storage.get("refresh_token"),
        "session-B-refresh"
    );
});