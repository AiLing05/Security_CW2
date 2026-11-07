const { randomBytes, timingSafeEqual } = require("node:crypto");
const { Readable } = require("node:stream");
const { pipeline } = require("node:stream/promises");

function createHandler({ upstream = process.env.DAM_INTERNAL_API_URL || "http://127.0.0.1:8000/api",
  origin = process.env.DAM_FRONTEND_ORIGIN || (process.env.NODE_ENV === "development" ? "http://localhost:3000" : "https://localhost:3443"),
  request = fetch } = {}) {
  const base = new URL(upstream);
  const site = new URL(origin);
  if ((base.protocol !== "https:" && !(base.protocol === "http:" && ["localhost", "127.0.0.1", "[::1]"].includes(base.hostname))) ||
      base.username || base.password || base.search || base.hash || !/^\/api\/?$/.test(base.pathname)) throw new Error("Invalid internal API address.");
  if (site.origin !== origin || (site.protocol !== "https:" && !(site.protocol === "http:" && site.hostname === "localhost"))) throw new Error("Invalid frontend origin.");
  const secure = site.protocol === "https:";
  const prefix = secure ? "__Host-dam_" : "dam_";
  const names = { access: prefix + "access", refresh: prefix + "refresh", csrf: prefix + "csrf" };
  const cookie = (name, value, age) => `${name}=${encodeURIComponent(value)}; Path=/; HttpOnly; SameSite=Strict; Max-Age=${age}${secure ? "; Secure" : ""}`;
  const clear = (res) => res.setHeader("Set-Cookie", [cookie(names.access, "", 0), cookie(names.refresh, "", 0)]);
  const lifetime = (token, limit) => {
    const exp = JSON.parse(Buffer.from(token.split(".")[1], "base64url").toString()).exp;
    if (!Number.isFinite(exp)) throw new Error("Invalid authentication response.");
    return Math.max(0, Math.min(limit, Math.floor(exp - Date.now() / 1000)));
  };
  const save = (res, data) => {
    if (typeof data.access !== "string" || typeof data.refresh !== "string") throw new Error("Invalid authentication response.");
    res.setHeader("Set-Cookie", [cookie(names.access, data.access, lifetime(data.access, 86400)), cookie(names.refresh, data.refresh, lifetime(data.refresh, 86400))]);
  };
  return async function handler(req, res) {
    res.setHeader("Cache-Control", "no-store");
    res.setHeader("X-Content-Type-Options", "nosniff");
    const json = (status, body) => { res.statusCode = status; res.setHeader("Content-Type", "application/json"); res.end(JSON.stringify(body)); };
    try {
      const cookies = {};
      for (const pair of (req.headers.cookie || "").split(";")) {
        const index = pair.indexOf("=");
        if (index < 0) continue;
        const name = pair.slice(0, index).trim();
        if (Object.values(names).includes(name) && Object.hasOwn(cookies, name)) return json(400, { detail: "Ambiguous session cookies." });
        cookies[name] = decodeURIComponent(pair.slice(index + 1));
      }
      const method = req.method.toUpperCase();
      const url = new URL(req.url, origin);
      const path = url.pathname.replace(/^\/api\//, "").replace(/\/$/, "");
      if (req.headers["sec-fetch-site"] === "cross-site") return json(403, { detail: "Cross-site request rejected." });
      if (path === "auth/csrf" && method === "GET") {
        if (req.headers.origin && req.headers.origin !== origin) return json(403, { detail: "Origin rejected." });
        const token = /^[a-f0-9]{64}$/.test(cookies[names.csrf] || "") ? cookies[names.csrf] : randomBytes(32).toString("hex");
        res.setHeader("Set-Cookie", cookie(names.csrf, token, 86400));
        return json(200, { csrfToken: token });
      }
      if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
        const expected = cookies[names.csrf] || "";
        const supplied = req.headers["x-csrf-token"] || "";
        if (req.headers.origin !== origin || !/^[a-f0-9]{64}$/.test(expected) || typeof supplied !== "string" ||
            supplied.length !== expected.length || !timingSafeEqual(Buffer.from(supplied), Buffer.from(expected))) return json(403, { detail: "CSRF verification failed.", code: "csrf_failed" });
      }
      const auth = ["token", "token/refresh", "logout"].includes(path);
      if (auth && method !== "POST") return json(405, { detail: "Use POST for authentication requests." });
      if (!auth && (!/^(users|assets|categories|tags|versions|me|audit)(\/|$)/.test(path) || !path.split("/").every((part) => /^[A-Za-z0-9_-]+$/.test(part)))) return json(404, { detail: "Not found." });
      let body;
      if (!["GET", "HEAD"].includes(method)) {
        const chunks = [];
        let size = 0;
        for await (const chunk of req) {
          size += chunk.length;
          if (size > 51 * 1024 * 1024) return json(413, { detail: "Request is too large." });
          chunks.push(chunk);
        }
        body = Buffer.concat(chunks);
      }
      const headers = { Accept: "application/json" };
      if (req.headers["content-type"]) headers["Content-Type"] = req.headers["content-type"];
      if (secure) headers["X-Forwarded-Proto"] = "https";
      if (path !== "token" && cookies[names.access]) headers.Authorization = `Bearer ${cookies[names.access]}`;
      if (path === "token/refresh" || path === "logout") {
        if (!cookies[names.refresh]) { clear(res); return json(path === "logout" ? 200 : 401, { detail: path === "logout" ? "Signed out." : "Sign in again." }); }
        body = JSON.stringify({ refresh: cookies[names.refresh] });
        headers["Content-Type"] = "application/json";
      }
      const response = await request(`${base.href.replace(/\/$/, "")}/${path}/${url.search}`, { method, headers, body, redirect: "manual", signal: AbortSignal.timeout(60000) });
      if (path === "token" || path === "token/refresh") {
        const data = await response.json();
        if (response.ok) { save(res, data); return json(200, { authenticated: true }); }
        if (path === "token/refresh" && response.status === 401) clear(res);
        return json(response.status, { detail: typeof data.detail === "string" ? data.detail : "Authentication failed." });
      }
      if (path === "logout") {
        if (response.ok) clear(res);
        return json(response.status, { detail: response.ok ? "Signed out." : "Logout could not be completed. Please retry." });
      }
      res.statusCode = response.status;
      for (const name of ["content-type", "content-disposition", "retry-after"]) {
        if (response.headers.has(name)) res.setHeader(name, response.headers.get(name));
      }
      if (!response.body || method === "HEAD") return res.end();
      await pipeline(Readable.fromWeb(response.body), res);
    } catch {
      if (!res.headersSent) json(502, { detail: "The API is unavailable. Please retry." });
      else res.destroy();
    }
  };
}

module.exports = { createHandler };
