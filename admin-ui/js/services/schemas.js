import { dataClient } from "./http.js";

export async function list() {
  return dataClient.request("GET", "/v1/dictionary/schemas");
}

export async function get(documentType) {
  return dataClient.request("GET", `/v1/dictionary/schemas/${encodeURIComponent(documentType)}`);
}
