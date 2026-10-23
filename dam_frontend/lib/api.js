// frontend/lib/api.js
export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api";

export async function postToken(username, password) {
  const res = await fetch(`${API_BASE}/token/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) throw new Error("Login failed");
  return res.json();
}

export async function fetchWithToken(endpoint, token, opts = {}) {
  const headers = { ...(opts.headers || {}), Authorization: `Bearer ${token}` };
  const res = await fetch(`${API_BASE}${endpoint}`, { ...opts, headers });
  if (!res.ok) throw res;
  return res.json();
}
