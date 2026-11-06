import {getAccessToken, refreshAccessToken} from "./tokenManager";
import {store} from "../redux/store";
import {logout} from "../redux/userSlice";

export const API_BASE =
    process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api";

export async function postToken(username, password) {
    const res = await fetch(`${API_BASE}/token/`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({username, password}),
    });

    if (!res.ok) throw new Error("Login failed");
    return res.json();
}

export async function fetchWithToken(endpoint, token, opts = {}) {
    const makeRequest = (accessToken) => {
        const headers = {
            ...(opts.headers || {}),
            Authorization: `Bearer ${accessToken}`,
        };

        return fetch(`${API_BASE}${endpoint}`, {
            ...opts,
            headers,
        });
    };

    // Prefer the latest token in storage, which may have been rotated.
    const access = getAccessToken() || token;
    const sessionRefresh = typeof window !== "undefined"
        ? localStorage.getItem("refresh_token")
        : null;

    let res = await makeRequest(access);

    // Retry only when authentication fails.

    if (res.status === 401) {
        try {
            const refreshedAccess = await refreshAccessToken();
            res = await makeRequest(refreshedAccess);
        } catch (error) {
            // Only log out when the refresh token was rejected.
            if (
                error.message === "Refresh token rejected." &&
                sessionRefresh &&
                !getAccessToken() &&
                !localStorage.getItem("refresh_token")
            ) {
                store.dispatch(logout());

                if (
                    typeof window !== "undefined" &&
                    window.location.pathname !== "/login"
                ) {
                    window.location.replace("/login");
                }
            }

            throw error;
        }
    }


    if (!res.ok) throw res;

    return res.json();
}
