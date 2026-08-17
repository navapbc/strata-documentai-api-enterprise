/**
 * Global tenant selector state.
 * Views render their own <select> and call mountSelect(el) on mount / unmountSelect(el) on unmount.
 */

import * as TenantsService from "../services/tenants.js";

let _currentTenantId = null;
let _options = []; // [{ value, label }] cached after first load
let _loading = false;
let _loaded = false;
const _listeners = [];
const _selects = new Set();

const STORAGE_KEY = "docai_selected_tenant";

export async function load() {
  if (_loaded || _loading) return;
  _loading = true;
  try {
    const resp = await TenantsService.list();
    _options = (resp.tenants || []).map((t) => ({ value: t.tenantId, label: t.tenantId }));
  } catch {
    // Tenant list unavailable (tenant-admin)
  }
  _loaded = true;
  _loading = false;

  const saved = sessionStorage.getItem(STORAGE_KEY);
  if (saved && _options.some((o) => o.value === saved)) {
    _currentTenantId = saved;
    _listeners.forEach((fn) => fn(_currentTenantId));
  }

  _selects.forEach(_populateSelect);
}

function _populateSelect(el) {
  el.replaceChildren();
  const defaultOpt = document.createElement("option");
  defaultOpt.value = "";
  defaultOpt.textContent = el.dataset.placeholder || "All Tenants";
  el.appendChild(defaultOpt);
  for (const { value, label } of _options) {
    const opt = document.createElement("option");
    opt.value = value;
    opt.textContent = label;
    el.appendChild(opt);
  }
  el.value = _currentTenantId || "";
}

export function mountSelect(el, { placeholder } = {}) {
  if (placeholder) el.dataset.placeholder = placeholder;
  _populateSelect(el);
  _selects.add(el);
  el.addEventListener("change", _onSelectChange);
}

export function unmountSelect(el) {
  _selects.delete(el);
  el.removeEventListener("change", _onSelectChange);
}

function _onSelectChange(e) {
  setTenantId(e.target.value || null);
}

export function getTenantId() {
  return _currentTenantId;
}

export function getOptions() {
  return _options;
}

export function onChange(fn) {
  _listeners.push(fn);
  return () => {
    const idx = _listeners.indexOf(fn);
    if (idx >= 0) _listeners.splice(idx, 1);
  };
}

export function setTenantId(tenantId) {
  _currentTenantId = tenantId || null;
  if (_currentTenantId) {
    sessionStorage.setItem(STORAGE_KEY, _currentTenantId);
  } else {
    sessionStorage.removeItem(STORAGE_KEY);
  }
  _selects.forEach((el) => {
    el.value = _currentTenantId || "";
  });
  _listeners.forEach((fn) => fn(_currentTenantId));
}
