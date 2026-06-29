import { adminClient } from "./http.js";

export async function get({ startDate, endDate, granularity = "daily", tenantId } = {}) {
  const params = new URLSearchParams();
  if (startDate) params.set("start_date", startDate);
  if (endDate) params.set("end_date", endDate);
  if (tenantId) params.set("tenant_id", tenantId);
  params.set("granularity", granularity);
  const qs = params.toString() ? `?${params}` : "";
  return adminClient.request("GET", `/v1/metrics${qs}`);
}
