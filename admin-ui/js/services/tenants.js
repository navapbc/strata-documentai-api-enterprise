import { adminClient } from "./http.js";

export async function list(activeOnly = true) {
  const qs = activeOnly ? "" : "?active_only=false";
  return adminClient.request("GET", `/v1/admin/tenants${qs}`);
}

export async function create(tenantId, displayName, primaryContact) {
  return adminClient.request("POST", "/v1/admin/tenants", {
    tenant_id: tenantId,
    display_name: displayName,
    primary_contact: primaryContact || null,
  });
}

export async function update(tenantId, { displayName, primaryContact, isActive } = {}) {
  const body = {};
  if (displayName !== undefined) body.display_name = displayName;
  if (primaryContact !== undefined) body.primary_contact = primaryContact;
  if (isActive !== undefined) body.is_active = isActive;
  return adminClient.request("PATCH", `/v1/admin/tenants/${encodeURIComponent(tenantId)}`, body);
}

export async function remove(tenantId) {
  return adminClient.request("DELETE", `/v1/admin/tenants/${encodeURIComponent(tenantId)}`);
}
