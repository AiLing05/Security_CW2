const API_BASE =
  process.env.NEXT_PUBLIC_API_URL;

let refreshPromise = null;
let refreshPromiseToken = null;

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

    const refresh = localStorage.getItem("refresh_token");

    if (!refresh) {
        throw new Error("No refresh token available.");
    }

// Share a refresh operation only within the same session.
    if (refreshPromise && refreshPromiseToken === refresh) {
        return refreshPromise;
    }

    refreshPromiseToken = refresh;

    const currentPromise = (async () => {

        const response = await fetch(`${API_BASE}/token/refresh/`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({refresh}),
        });


        if (response.status === 401) {
            // Clear tokens only if this is still the same session.
            if (localStorage.getItem("refresh_token") === refresh) {
                clearAuthTokens();
            }

            throw new Error("Refresh token rejected.");
        }

        if (!response.ok) {
            throw new Error(`Token refresh failed: HTTP ${response.status}`);
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

    refreshPromise = currentPromise;

    try {
        return await currentPromise;
    } finally {
        if (refreshPromise === currentPromise) {
            refreshPromise = null;
            refreshPromiseToken = null;
        }
    }
}
