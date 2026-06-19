import { adminClient } from "./http.js";

export async function list() {
  return adminClient.request("GET", "/v1/admin/users");
}

export async function approve(username, role, tenantId) {
  return adminClient.request("POST", `/v1/admin/users/${encodeURIComponent(username)}/approve`, {
    role,
    tenant_id: tenantId || null,
  });
}

export async function changeRole(username, role) {
  return adminClient.request("POST", `/v1/admin/users/${encodeURIComponent(username)}/role`, {
    role: role || null,
  });
}

export async function changeTenant(username, tenantId) {
  return adminClient.request("POST", `/v1/admin/users/${encodeURIComponent(username)}/tenant`, {
    tenant_id: tenantId || null,
  });
}

export async function remove(username) {
  return adminClient.request("DELETE", `/v1/admin/users/${encodeURIComponent(username)}`);
}
