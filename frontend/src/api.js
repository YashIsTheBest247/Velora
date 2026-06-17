// API base resolution:
// - Local Docker/dev: VITE_API_BASE is unset -> use the same-origin "/api"
//   prefix (nginx in prod-compose, or Vite's dev proxy, forwards it to FastAPI).
// - Render/cloud: VITE_API_BASE is set to the backend host (e.g.
//   "velora-api.onrender.com"); we normalise it to an absolute https URL and
//   call the API directly (CORS is enabled on the backend).
function normalizeBase(raw) {
  if (!raw) return "/api";
  let b = raw.trim().replace(/\/$/, "");
  if (!/^https?:\/\//.test(b)) b = `https://${b}`;
  return b;
}

export const API_BASE = normalizeBase(import.meta.env.VITE_API_BASE);

// Swagger UI lives at the backend root. Locally we hit the exposed :8000 port;
// in the cloud the API has its own origin, so just append /docs.
export const DOCS_URL =
  API_BASE === "/api"
    ? `${window.location.protocol}//${window.location.hostname}:8000/docs`
    : `${API_BASE}/docs`;

async function handle(res) {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch (_) {}
    throw new Error(detail);
  }
  return res.json();
}

export function uploadCsv(file) {
  const form = new FormData();
  form.append("file", file);
  return fetch(`${API_BASE}/jobs/upload`, { method: "POST", body: form }).then(handle);
}

export function listJobs(status) {
  const qs = status ? `?status=${encodeURIComponent(status)}` : "";
  return fetch(`${API_BASE}/jobs${qs}`).then(handle);
}

export function getStatus(jobId) {
  return fetch(`${API_BASE}/jobs/${jobId}/status`).then(handle);
}

export function getResults(jobId) {
  return fetch(`${API_BASE}/jobs/${jobId}/results`).then(handle);
}

export function deleteJob(jobId) {
  return fetch(`${API_BASE}/jobs/${jobId}`, { method: "DELETE" }).then((res) => {
    if (!res.ok) throw new Error("Failed to delete job.");
  });
}
