import { dataClient } from "./http.js";

export async function check() {
  return dataClient.request("GET", "/health");
}
