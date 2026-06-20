import { adminClient } from "../../../shared/services/http.js";

export async function list({ limit, cursor } = {}) {
  const params = new URLSearchParams();
  if (limit) params.set("limit", String(limit));
  if (cursor) params.set("cursor", cursor);
  const qs = params.toString() ? `?${params}` : "";
  return adminClient.request("GET", `/v1/demo/documents${qs}`);
}

export async function get(
  jobId,
  { includeExtractedData = false, includeBoundingBox = false } = {},
) {
  const params = new URLSearchParams();
  if (includeExtractedData) params.set("include_extracted_data", "true");
  if (includeBoundingBox) params.set("include_bounding_box", "true");
  const qs = params.toString() ? `?${params}` : "";
  return adminClient.request("GET", `/v1/demo/documents/${encodeURIComponent(jobId)}${qs}`);
}

export async function getPreviewUrl(jobId) {
  return adminClient.request("GET", `/v1/demo/documents/${encodeURIComponent(jobId)}/preview`);
}

export async function upload(file) {
  const baseUrl = adminClient.getBaseUrl();
  const session = JSON.parse(sessionStorage.getItem("docai_console_session") || "{}");
  const token = session.idToken || "";

  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${baseUrl}/v1/demo/documents`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: formData,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || "Upload failed");
  }

  return res.json();
}
