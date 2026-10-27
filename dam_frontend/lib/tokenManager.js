
const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api";

let refreshPromise = null;

export function getAccessToken() {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("access_token");
}

export function clearAuthTokens() {
  if (typeof window === "undefined") return;

  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
}

export async function refreshAccessToken() {
  if (typeof window === "undefined") {
    throw new Error("Token refresh requires a browser.");
  }

  // Share a single refresh operation among simultaneous callers.
  if (refreshPromise) {
    return refreshPromise;
  }

  refreshPromise = (async () => {
    const refresh = localStorage.getItem("refresh_token");

    if (!refresh) {
      throw new Error("No refresh token available.");
    }

    const response = await fetch(`${API_BASE}/token/refresh/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ refresh }),
    });

    if (!response.ok) {
      throw new Error("Refresh token rejected.");
    }

    const data = await response.json();

    if (!data.access || !data.refresh) {
      throw new Error("Invalid token refresh response.");
    }

    // SimpleJWT rotation requires saving the replacement refresh token.
    // Avoid restoring credentials after logout occurred mid-request.
    if (localStorage.getItem("refresh_token") !== refresh) {
      throw new Error("Authentication session changed during refresh.");
    }

    localStorage.setItem("access_token", data.access);
    localStorage.setItem("refresh_token", data.refresh);

    return data.access;
  })();

  try {
    return await refreshPromise;
  } finally {
    refreshPromise = null;
  }
}
