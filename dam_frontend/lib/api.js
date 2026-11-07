import { apiFetch } from "./apiFetch";

export const API_BASE = "/api";

export async function postToken(username, password) {
  const response = await apiFetch(`${API_BASE}/token/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!response.ok) throw new Error("Login failed");
  return response.json();
}

export async function fetchWithToken(endpoint, _session, options = {}) {
  const response = await apiFetch(`${API_BASE}${endpoint}`, options);
  if (!response.ok) throw response;
  return response.json();
}
