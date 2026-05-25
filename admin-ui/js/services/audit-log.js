import { adminClient } from "./http.js";

export async function list({ tenantId, action, startDate, endDate, limit, cursor } = {}) {
  const params = new URLSearchParams();
  if (tenantId) params.set("tenant_id", tenantId);
  if (action) params.set("action", action);
  if (startDate) params.set("start_date", startDate);
  if (endDate) params.set("end_date", endDate);
  if (limit) params.set("limit", String(limit));
  if (cursor) params.set("cursor", cursor);
  const qs = params.toString() ? `?${params}` : "";
  return adminClient.request("GET", `/v1/admin/audit-log${qs}`);
}

export async function listActions() {
  return adminClient.request("GET", "/v1/admin/audit-log/actions");
}
