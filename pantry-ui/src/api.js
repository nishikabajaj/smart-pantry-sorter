// ─── API HELPERS ──────────────────────────────────────────────────────────────
// All communication with the Flask backend lives here.
// Base URL can be overridden with REACT_APP_API_URL in a .env file.

export const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:5000';

export async function apiGet(path) {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function apiPost(path, body) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}