import { dataClient } from "./http.js";

export async function get(tenantId, documentType) {
  return dataClient.request("GET", `/v1/config/extraction-rules?tenant_id=${encodeURIComponent(tenantId)}&document_type=${encodeURIComponent(documentType)}`);
}

export async function save(tenantId, documentType, requiredFields, optionalFields) {
  return dataClient.request("PUT", "/v1/config/extraction-rules", {
    tenant_id: tenantId,
    document_type: documentType,
    required_fields: requiredFields,
    optional_fields: optionalFields,
  });
}

export async function remove(tenantId, documentType) {
  return dataClient.request("DELETE", `/v1/config/extraction-rules?tenant_id=${encodeURIComponent(tenantId)}&document_type=${encodeURIComponent(documentType)}`);
}
