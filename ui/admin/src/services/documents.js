import { adminClient } from "./http.js";

export async function list({ tenantId, status, isDemo, limit, cursor } = {}) {
  const params = new URLSearchParams();
  if (tenantId) params.set("tenant_id", tenantId);
  if (status) params.set("status_filter", status);
  if (isDemo != null) params.set("is_demo", String(isDemo));
  if (limit) params.set("limit", String(limit));
  if (cursor) params.set("cursor", cursor);
  const qs = params.toString() ? `?${params}` : "";
  return adminClient.request("GET", `/v1/admin/documents${qs}`);
}

export async function get(
  jobId,
  { includeExtractedData = false, includeBoundingBox = false } = {},
) {
  const params = new URLSearchParams();
  if (includeExtractedData) params.set("include_extracted_data", "true");
  if (includeBoundingBox) params.set("include_bounding_box", "true");
  const qs = params.toString() ? `?${params}` : "";
  return adminClient.request("GET", `/v1/admin/documents/${encodeURIComponent(jobId)}${qs}`);
}

export async function getPreviewUrl(jobId) {
  return adminClient.request("GET", `/v1/admin/documents/${encodeURIComponent(jobId)}/preview`);
}

export async function search({
  tenantId,
  filename,
  dateFrom,
  dateTo,
  userProvidedDocumentType,
  matchedBlueprintName,
  limit,
  cursor,
} = {}) {
  const params = new URLSearchParams();
  if (tenantId) params.set("tenant_id", tenantId);
  if (filename) params.set("filename", filename);
  if (dateFrom) params.set("date_from", dateFrom);
  if (dateTo) params.set("date_to", dateTo);
  if (userProvidedDocumentType) params.set("user_provided_document_type", userProvidedDocumentType);
  if (matchedBlueprintName) params.set("matched_blueprint_name", matchedBlueprintName);
  if (limit) params.set("limit", String(limit));
  if (cursor) params.set("cursor", cursor);
  const qs = params.toString() ? `?${params}` : "";
  return adminClient.request("GET", `/v1/admin/search/documents${qs}`);
}
