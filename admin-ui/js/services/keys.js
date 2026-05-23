import { adminClient } from "./http.js";

export async function list({ clientName, includeInactive } = {}) {
  const params = new URLSearchParams();
  if (clientName) params.set("client_name", clientName);
  if (includeInactive) params.set("include_inactive", "true");
  const qs = params.toString() ? `?${params}` : "";
  return adminClient.request("GET", `/v1/admin/api-keys${qs}`);
}

export async function create(clientName, environment, expiresAt, emailAddress) {
  const body = { client_name: clientName, environment };
  if (expiresAt) body.expires_at = expiresAt;
  if (emailAddress) body.email_address = emailAddress;
  return adminClient.request("POST", "/v1/admin/api-keys", body);
}

export async function revoke(keyPrefix) {
  return adminClient.request("DELETE", `/v1/admin/api-keys/${encodeURIComponent(keyPrefix)}`);
}
