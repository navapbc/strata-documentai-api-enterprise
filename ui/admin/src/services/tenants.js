import { adminClient } from "./http.js";

export async function list(activeOnly = true) {
  const qs = activeOnly ? "" : "?active_only=false";
  return adminClient.request("GET", `/v1/admin/tenants${qs}`);
}

export async function create(
  tenantId,
  displayName,
  primaryContact,
  maxWritesPerDay,
  maxWritesPerMonth,
  extractionConfidenceFloor,
) {
  return adminClient.request("POST", "/v1/admin/tenants", {
    tenant_id: tenantId,
    display_name: displayName,
    primary_contact: primaryContact || null,
    max_writes_per_day: maxWritesPerDay || null,
    max_writes_per_month: maxWritesPerMonth || null,
    extraction_confidence_floor: extractionConfidenceFloor ?? null,
  });
}

export async function update(
  tenantId,
  {
    displayName,
    primaryContact,
    isActive,
    maxWritesPerDay,
    maxWritesPerMonth,
    extractionConfidenceFloor,
  } = {},
) {
  const body = {};
  if (displayName !== undefined) body.display_name = displayName;
  if (primaryContact !== undefined) body.primary_contact = primaryContact;
  if (isActive !== undefined) body.is_active = isActive;
  if (maxWritesPerDay !== undefined) body.max_writes_per_day = maxWritesPerDay;
  if (maxWritesPerMonth !== undefined) body.max_writes_per_month = maxWritesPerMonth;
  if (extractionConfidenceFloor !== undefined)
    body.extraction_confidence_floor = extractionConfidenceFloor;
  return adminClient.request("PATCH", `/v1/admin/tenants/${encodeURIComponent(tenantId)}`, body);
}

export async function remove(tenantId) {
  return adminClient.request("DELETE", `/v1/admin/tenants/${encodeURIComponent(tenantId)}`);
}
