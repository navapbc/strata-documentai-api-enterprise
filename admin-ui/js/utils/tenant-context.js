/**
 * Global tenant selector state.
 * Views read the current tenant from here instead of managing their own selectors.
 */

import * as TenantsService from "../services/tenants.js";

let _select = null;
let _currentTenantId = null;
const _listeners = [];

export function init(selectEl) {
  _select = selectEl;
  _select.addEventListener("change", () => {
    _currentTenantId = _select.value || null;
    _listeners.forEach((fn) => fn(_currentTenantId));
  });
}

let _loading = false;

export async function load() {
  if (!_select || _loading) return;
  _loading = true;
  const current = _select.value;
  _select.innerHTML = '<option value="">All Tenants</option>';
  try {
    const resp = await TenantsService.list();
    for (const tenant of resp.tenants || []) {
      const opt = document.createElement("option");
      opt.value = tenant.tenantId;
      opt.textContent = tenant.tenantId;
      _select.appendChild(opt);
    }
  } catch {
    // Tenant list unavailable (tenant-admin)
  }
  if (current) _select.value = current;
  _loading = false;
}

export function getTenantId() {
  return _currentTenantId;
}

export function onChange(fn) {
  _listeners.push(fn);
  return () => {
    const idx = _listeners.indexOf(fn);
    if (idx >= 0) _listeners.splice(idx, 1);
  };
}

export function setTenantId(tenantId) {
  _currentTenantId = tenantId;
  if (_select) _select.value = tenantId || "";
  _listeners.forEach((fn) => fn(_currentTenantId));
}
