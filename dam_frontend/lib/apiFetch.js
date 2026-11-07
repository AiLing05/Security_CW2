let csrfPromise;
let refreshPromise;

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
  if (!["GET", "HEAD", "OPTIONS"].includes(method)) headers.set("X-CSRF-Token", await csrfToken());
  const response = await fetch(target.href, { ...options, headers, credentials: "same-origin", cache: "no-store" });
  if (response.status === 403 && csrfRetry) {
    const error = await response.clone().json().catch(() => ({}));
    if (error.code === "csrf_failed") {
      resetCsrfToken();
      return apiFetch(url, options, retry, false);
    }
  }
  if (response.status === 401 && retry && !/\/(token|logout)(\/|$)/.test(target.pathname)) {
    if (!refreshPromise) {
      refreshPromise = apiFetch("/api/token/refresh/", { method: "POST" }, false)
        .finally(() => { refreshPromise = undefined; });
    }
    const refreshed = await refreshPromise;
    if (refreshed.ok) return apiFetch(url, options, false);
  }
  return response;
}
