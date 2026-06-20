/**
 * Global tenant selector state.
 * Views read the current tenant from here instead of managing their own selectors.
 */

import * as TenantsService from "../services/tenants.js";

let _select = null;
let _currentTenantId = null;
const _listeners = [];

const STORAGE_KEY = "docai_selected_tenant";

export function init(selectEl) {
  _select = selectEl;
  _select.innerHTML = '<option value="">Loading tenants...</option>';
  _select.disabled = true;
  _select.addEventListener("change", () => {
    _currentTenantId = _select.value || null;
    if (_currentTenantId) {
      sessionStorage.setItem(STORAGE_KEY, _currentTenantId);
    } else {
      sessionStorage.removeItem(STORAGE_KEY);
    }
    _listeners.forEach((fn) => fn(_currentTenantId));
  });
}

let _loading = false;

export async function load() {
  if (!_select || _loading) return;
  _loading = true;
  const current = _select.value;
  _select.innerHTML = '<option value="">All Tenants</option>';
  _select.disabled = false;
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
  // Restore from sessionStorage if no value set yet
  const saved = sessionStorage.getItem(STORAGE_KEY);
  if (current) {
    _select.value = current;
  } else if (saved && _select.querySelector(`option[value="${saved}"]`)) {
    _select.value = saved;
    _currentTenantId = saved;
    _listeners.forEach((fn) => fn(_currentTenantId));
  }
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
