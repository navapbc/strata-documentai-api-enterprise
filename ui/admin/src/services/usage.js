import { adminClient } from "./http.js";

export async function get({ month, granularity = "monthly" } = {}) {
  const params = new URLSearchParams();
  if (month) params.set("month", month);
  params.set("granularity", granularity);
  const qs = params.toString() ? `?${params}` : "";
  return adminClient.request("GET", `/v1/admin/usage${qs}`);
}
