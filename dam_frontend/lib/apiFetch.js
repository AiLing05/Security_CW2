let csrfPromise;
let refreshPromise;
let refreshController;
let sessionVersion = 0;

async function csrfToken() {
  if (!csrfPromise) {
    csrfPromise = fetch("/api/auth/csrf/", { credentials: "same-origin", cache: "no-store" })
      .then(async (response) => {
        if (!response.ok) throw new Error("Could not initialize request protection.");
        return (await response.json()).csrfToken;
      }).catch((error) => { csrfPromise = undefined; throw error; });
  }
  return csrfPromise;
}

export function resetCsrfToken() {
  csrfPromise = undefined;
}

export async function apiFetch(url, options = {}, retry = true, csrfRetry = true) {
  const target = new URL(url, window.location.origin);
  if (target.origin !== window.location.origin || !target.pathname.startsWith("/api/")) {
    throw new Error("Authenticated requests must use the same-origin API.");
  }
  const headers = new Headers(options.headers);
  headers.delete("Authorization");
  const method = (options.method || "GET").toUpperCase();
  if (method === "POST" && /\/(token|logout)\/?$/.test(target.pathname)) {
    if (/\/logout\/?$/.test(target.pathname) && refreshPromise) await refreshPromise.catch(() => {});
    sessionVersion++;
    refreshController?.abort();
    refreshController = undefined;
    refreshPromise = undefined;
  }
  const version = sessionVersion;
  if (!["GET", "HEAD", "OPTIONS"].includes(method)) headers.set("X-CSRF-Token", await csrfToken());
  if (version !== sessionVersion) throw new Error("Authentication session changed.");
  const response = await fetch(target.href, { ...options, headers, credentials: "same-origin", cache: "no-store" });
  if (version !== sessionVersion) throw new Error("Authentication session changed.");
  if (response.status === 403 && csrfRetry) {
    const error = await response.clone().json().catch(() => ({}));
    if (error.code === "csrf_failed") {
      resetCsrfToken();
      return apiFetch(url, options, retry, false);
    }
  }
  if (response.status === 401 && retry && !/\/(token|logout)(\/|$)/.test(target.pathname)) {
    if (!refreshPromise) {
      const controller = new AbortController();
      refreshController = controller;
      const pending = apiFetch("/api/token/refresh/", { method: "POST", signal: controller.signal }, false)
        .finally(() => {
          if (refreshPromise === pending) { refreshPromise = undefined; refreshController = undefined; }
        });
      refreshPromise = pending;
    }
    const refreshed = await refreshPromise;
    if (version !== sessionVersion) throw new Error("Authentication session changed.");
    if (refreshed.ok) return apiFetch(url, options, false);
    if (refreshed.status === 401) {
      window.dispatchEvent(new Event("dam:session-expired"));
    } else {
      throw new Error(`Token refresh failed: HTTP ${refreshed.status}`);
    }
  }
  return response;
}
