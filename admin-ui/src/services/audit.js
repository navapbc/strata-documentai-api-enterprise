import { adminClient } from "./http.js";

export async function reportLogin(email) {
  try {
    await adminClient.request("POST", "/v1/audit/auth-event", {
      action: "login",
      email,
    });
  } catch {
    // Best-effort - don't block the login flow
  }
}

export async function reportLogout(email) {
  try {
    await adminClient.request("POST", "/v1/audit/auth-event", {
      action: "logout",
      email,
    });
  } catch {
    // Best-effort
  }
}
