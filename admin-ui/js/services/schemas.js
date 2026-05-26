import { adminClient } from "./http.js";

export async function list() {
  return adminClient.request("GET", "/v1/dictionary/schemas");
}

export async function get(documentType) {
  return adminClient.request("GET", `/v1/dictionary/schemas/${encodeURIComponent(documentType)}`);
}

export async function getAllFields() {
  return adminClient.request("GET", "/v1/dictionary/fields");
}

export async function getCategories() {
  return adminClient.request("GET", "/v1/dictionary/document-categories");
}
