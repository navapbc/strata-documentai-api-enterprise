import { adminClient } from "./http.js";

export async function list({ apiKeyName, includeInactive, tenantId } = {}) {
  const params = new URLSearchParams();
  if (apiKeyName) params.set("api_key_name", apiKeyName);
  if (includeInactive) params.set("include_inactive", "true");
  if (tenantId) params.set("tenant_id", tenantId);
  const qs = params.toString() ? `?${params}` : "";
  return adminClient.request("GET", `/v1/admin/api-keys${qs}`);
}

export async function create(apiKeyName, environment, expiresAt, emailAddress, tenantId) {
  const body = { api_key_name: apiKeyName, environment };
  if (expiresAt) body.expires_at = expiresAt;
  if (emailAddress) body.email_address = emailAddress;
  if (tenantId) body.tenant_id = tenantId;
  return adminClient.request("POST", "/v1/admin/api-keys", body);
}

export async function revoke(keyPrefix) {
  return adminClient.request("DELETE", `/v1/admin/api-keys/${encodeURIComponent(keyPrefix)}`);
}
