import test from "node:test";
import assert from "node:assert/strict";
import http from "node:http";
import { once } from "node:events";
import auth from "../lib/serverAuth.cjs";

for (const failure of ["server", "network"]) {
  test(`${failure} refresh failure does not clear existing HttpOnly cookies`, async (t) => {
    const server = http.createServer(auth.createHandler({
      origin: "https://localhost:3443",
      request: async () => {
        if (failure === "network") throw new Error("Network unavailable");
        return Response.json({ detail: "Retry later" }, { status: 500 });
      },
    })).listen(0, "127.0.0.1");
    await once(server, "listening");
    t.after(() => new Promise(resolve => { server.closeAllConnections(); server.close(resolve); }));
    const base = `http://127.0.0.1:${server.address().port}/api/`;
    const init = await fetch(base + "auth/csrf");
    const csrf = (await init.json()).csrfToken;
    const response = await fetch(base + "token/refresh", { method: "POST", headers: {
      Origin: "https://localhost:3443", "X-CSRF-Token": csrf,
      Cookie: `${init.headers.getSetCookie()[0].split(";")[0]}; __Host-dam_refresh=existing-refresh`,
    } });
    assert.equal(response.status, failure === "network" ? 502 : 500);
    assert.deepEqual(response.headers.getSetCookie(), []);
  });
}
