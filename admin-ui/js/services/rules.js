import { adminClient } from "./http.js";

export async function list(tenantId) {
  const params = tenantId ? `?tenant_id=${encodeURIComponent(tenantId)}` : "";
  return adminClient.request("GET", `/v1/config/extraction-rules${params}`);
}

export async function put(
  tenantId,
  documentType,
  requiredFields,
  optionalFields,
  blueprintArn = null,
) {
  const body = {
    tenant_id: tenantId,
    document_type: documentType,
    required_fields: requiredFields,
    optional_fields: optionalFields,
  };
  if (blueprintArn) body.blueprint_arn = blueprintArn;
  return adminClient.request("PUT", "/v1/config/extraction-rules", body);
}

export async function get(tenantId, documentType) {
  const params = `?tenant_id=${encodeURIComponent(tenantId)}&document_type=${encodeURIComponent(documentType)}`;
  return adminClient.request("GET", `/v1/config/extraction-rules${params}`);
}

export async function remove(tenantId, documentType) {
  const params = `?tenant_id=${encodeURIComponent(tenantId)}&document_type=${encodeURIComponent(documentType)}`;
  return adminClient.request("DELETE", `/v1/config/extraction-rules${params}`);
}
