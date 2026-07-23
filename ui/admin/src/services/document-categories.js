import { adminClient } from "./http.js";

export async function list(tenantId, activeOnly = true) {
  const params = new URLSearchParams();
  if (tenantId) params.set("tenant_id", tenantId);
  if (!activeOnly) params.set("active_only", "false");
  const qs = params.toString() ? `?${params}` : "";
  return adminClient.request("GET", `/v1/admin/document-categories${qs}`);
}

export async function create(
  tenantId,
  categoryName,
  displayName,
  description,
  processingPercentage,
) {
  const params = tenantId ? `?tenant_id=${encodeURIComponent(tenantId)}` : "";
  return adminClient.request("POST", `/v1/admin/document-categories${params}`, {
    category_name: categoryName,
    display_name: displayName,
    description: description || null,
    processing_percentage: processingPercentage,
  });
}

export async function update(
  tenantId,
  categoryName,
  { displayName, description, isActive, processingPercentage } = {},
) {
  const params = tenantId ? `?tenant_id=${encodeURIComponent(tenantId)}` : "";
  const body = {};
  if (displayName !== undefined) body.display_name = displayName;
  if (description !== undefined) body.description = description;
  if (isActive !== undefined) body.is_active = isActive;
  if (processingPercentage !== undefined) body.processing_percentage = processingPercentage;
  return adminClient.request(
    "PATCH",
    `/v1/admin/document-categories/${encodeURIComponent(categoryName)}${params}`,
    body,
  );
}

export async function remove(tenantId, categoryName) {
  const params = tenantId ? `?tenant_id=${encodeURIComponent(tenantId)}` : "";
  return adminClient.request(
    "DELETE",
    `/v1/admin/document-categories/${encodeURIComponent(categoryName)}${params}`,
  );
}
