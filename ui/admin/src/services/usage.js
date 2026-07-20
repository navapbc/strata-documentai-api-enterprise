import { adminClient } from "./http.js";

export async function get({ month, granularity = "monthly", tenantId } = {}) {
  const params = new URLSearchParams();
  if (month) params.set("month", month);
  if (tenantId) params.set("tenant_id", tenantId);
  params.set("granularity", granularity);
  const qs = params.toString() ? `?${params}` : "";
  return adminClient.request("GET", `/v1/admin/usage${qs}`);
}
