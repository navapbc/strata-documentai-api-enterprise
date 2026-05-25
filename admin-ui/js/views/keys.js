import * as Helpers from "../utils/helpers.js";
import * as KeysService from "../services/keys.js";
import * as TenantContext from "../utils/tenant-context.js";
import { DEMO_KEYS } from "../demo/keys.js";

let _tbody, _noKeys, _createKeyBtn, _isDemo = false;
let _createModal, _createForm, _cancelCreate;
let _keyCreatedModal, _newKeyValue, _copyKeyBtn, _closeCreated;
let _refreshKeysBtn;
let _revokeModal, _revokeKeyPrefix, _cancelRevoke, _confirmRevoke;
let _pendingRevokeKey = null;
let _showInactiveToggle;

export function init({ tbody, noKeys, createKeyBtn, createModal, createForm, cancelCreate,
                       keyCreatedModal, newKeyValue, copyKeyBtn, closeCreated, refreshKeysBtn }) {
  _tbody = tbody;
  _noKeys = noKeys;
  _createKeyBtn = createKeyBtn;
  _createModal = createModal;
  _createForm = createForm;
  _cancelCreate = cancelCreate;
  _keyCreatedModal = keyCreatedModal;
  _newKeyValue = newKeyValue;
  _copyKeyBtn = copyKeyBtn;
  _closeCreated = closeCreated;
  _refreshKeysBtn = refreshKeysBtn;

  _createKeyBtn.addEventListener("click", openCreateModal);
  _cancelCreate.addEventListener("click", () => { _createModal.classList.add("hidden"); });
  _createForm.addEventListener("submit", handleCreate);

  TenantContext.onChange(() => load());
  _copyKeyBtn.addEventListener("click", copyKey);
  _closeCreated.addEventListener("click", () => { _keyCreatedModal.classList.add("hidden"); });
  _refreshKeysBtn.addEventListener("click", () => { _isDemo ? render(DEMO_KEYS) : load(); });

  _showInactiveToggle = document.getElementById("show-inactive-keys");
  if (_showInactiveToggle) {
    _showInactiveToggle.addEventListener("change", () => {
      _isDemo ? render(DEMO_KEYS) : load();
    });
  }

  _revokeModal = document.getElementById("revoke-modal");
  _revokeKeyPrefix = document.getElementById("revoke-key-prefix");
  _cancelRevoke = document.getElementById("cancel-revoke");
  _confirmRevoke = document.getElementById("confirm-revoke");
  _cancelRevoke.addEventListener("click", closeRevokeModal);
  _confirmRevoke.addEventListener("click", handleConfirmRevoke);
}

function openRevokeModal(keyPrefix) {
  _pendingRevokeKey = keyPrefix;
  _revokeKeyPrefix.textContent = keyPrefix;
  _revokeModal.classList.remove("hidden");
}

function closeRevokeModal() {
  _pendingRevokeKey = null;
  _revokeModal.classList.add("hidden");
}

async function handleConfirmRevoke() {
  if (!_pendingRevokeKey) return;
  const keyPrefix = _pendingRevokeKey;
  closeRevokeModal();
  try {
    await KeysService.revoke(keyPrefix);
    await load();
  } catch (e) {
    alert(`Failed to revoke: ${e.message}`);
  }
}

export function setDemo(val) { _isDemo = val; }

function openCreateModal() {
  _createModal.classList.remove("hidden");
  const tenantSelect = document.getElementById("key-tenant");
  // Populate tenant dropdown from global context
  if (tenantSelect.options.length <= 1) {
    import("../utils/tenant-context.js").then(async (TenantContext) => {
      await TenantContext.load();
    });
  }
  // Sync options from global selector
  const globalSelect = document.getElementById("global-tenant-select");
  tenantSelect.innerHTML = '<option value="">\u2014 Select tenant \u2014</option>';
  for (const opt of globalSelect.options) {
    if (opt.value) {
      const newOpt = document.createElement("option");
      newOpt.value = opt.value;
      newOpt.textContent = opt.textContent;
      tenantSelect.appendChild(newOpt);
    }
  }
  document.getElementById("api-key-name").value = "";
  document.getElementById("client-environment").value = "dev";
  document.getElementById("client-email").value = "";
}

async function handleCreate(e) {
  e.preventDefault();
  const tenantId = document.getElementById("key-tenant").value.trim();
  const apiKeyName = document.getElementById("api-key-name").value.trim();
  const environment = document.getElementById("client-environment").value.trim() || "dev";
  const emailAddress = document.getElementById("client-email").value.trim() || undefined;
  try {
    const result = _isDemo
      ? { api_key: `docai_${Math.random().toString(36).slice(2, 18)}` }
      : await KeysService.create(apiKeyName, environment, undefined, emailAddress, tenantId);
    _createModal.classList.add("hidden");
    _newKeyValue.textContent = result.apiKey || "—";
    _keyCreatedModal.classList.remove("hidden");
    if (_isDemo) {
      DEMO_KEYS.push({
        api_key_name: apiKeyName,
        environment,
        keyPrefix: result.apiKey.slice(0, 12) + "...",
        created_at: new Date().toISOString(),
        is_active: true,
      });
      render(DEMO_KEYS);
    } else {
      await load();
    }
  } catch (err) { alert(`Failed to create key: ${err.message}`); }
}

function copyKey() {
  navigator.clipboard.writeText(_newKeyValue.textContent);
  _copyKeyBtn.textContent = "Copied!";
  setTimeout(() => (_copyKeyBtn.textContent = "Copy"), 2000);
}

export function render(keys) {
  _tbody.innerHTML = "";
  if (keys.length === 0) { _noKeys.classList.remove("hidden"); return; }
  _noKeys.classList.add("hidden");
  for (const key of keys) {
    const tr = document.createElement("tr");
    const isActive = key.isActive !== false;
    if (!isActive) tr.classList.add("row-inactive");
    const actionCell = isActive
      ? `<button class="btn-danger btn-sm">Revoke</button>`
      : `<span class="badge badge-revoked">Revoked</span>`;
    tr.innerHTML = `
      <td>${Helpers.esc(key.tenantId || "—")}</td>
      <td>${Helpers.esc(key.apiKeyName || "—")}</td>
      <td>${Helpers.esc(key.emailAddress || "—")}</td>
      <td>${Helpers.esc(key.environment || "—")}</td>
      <td><code>${key.keyPrefix ? Helpers.esc(key.keyPrefix) + "…" : "—"}</code></td>
      <td>${Helpers.formatDate(key.createdAt)}</td>
      <td>${key.lastUsed ? Helpers.formatDate(key.lastUsed) : "—"}</td>
      <td>${actionCell}</td>
    `;
    if (isActive) {
      tr.querySelector("button").addEventListener("click", () => {
        if (_isDemo) { tr.remove(); if (!_tbody.children.length) _noKeys.classList.remove("hidden"); }
        else openRevokeModal(key.keyPrefix);
      });
    }
    _tbody.appendChild(tr);
  }
}

export async function load() {
  try {
    const includeInactive = _showInactiveToggle?.checked || false;
    const tenantId = TenantContext.getTenantId();
    const data = await KeysService.list({ includeInactive, tenantId });
    render(data.keys || []);
  } catch (e) {
    _tbody.innerHTML = "";
    _noKeys.textContent = e.message;
    _noKeys.classList.remove("hidden");
  }
}

