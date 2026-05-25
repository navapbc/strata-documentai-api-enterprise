import { adminClient } from "./http.js";

export async function list({ tenantId, status, limit, cursor } = {}) {
  const params = new URLSearchParams();
  if (tenantId) params.set("tenant_id", tenantId);
  if (status) params.set("status_filter", status);
  if (limit) params.set("limit", String(limit));
  if (cursor) params.set("cursor", cursor);
  const qs = params.toString() ? `?${params}` : "";
  return adminClient.request("GET", `/v1/admin/documents${qs}`);
}

export async function get(jobId) {
  return adminClient.request("GET", `/v1/admin/documents/${encodeURIComponent(jobId)}`);
}
