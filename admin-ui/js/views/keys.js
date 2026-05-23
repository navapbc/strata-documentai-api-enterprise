import * as Helpers from "../utils/helpers.js";
import * as KeysService from "../services/keys.js";
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
  document.getElementById("toggle-advanced").addEventListener("click", () => {
    const fields = document.getElementById("advanced-fields");
    const toggle = document.getElementById("toggle-advanced");
    const isHidden = fields.classList.toggle("hidden");
    toggle.textContent = isHidden ? "Show advanced options" : "Hide advanced options";
  });
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
  document.getElementById("client-name").value = "";
  document.getElementById("client-environment").value = "dev";
  document.getElementById("client-expires-at").value = "";
  document.getElementById("client-email").value = "";
  document.getElementById("advanced-fields").classList.add("hidden");
  document.getElementById("toggle-advanced").textContent = "Show advanced options";
}

async function handleCreate(e) {
  e.preventDefault();
  const clientName = document.getElementById("client-name").value.trim();
  const environment = document.getElementById("client-environment").value.trim() || "dev";
  const expiresAt = document.getElementById("client-expires-at").value.trim() || undefined;
  const emailAddress = document.getElementById("client-email").value.trim() || undefined;
  try {
    const result = _isDemo
      ? { api_key: `docai_${Math.random().toString(36).slice(2, 18)}` }
      : await KeysService.create(clientName, environment, expiresAt, emailAddress);
    _createModal.classList.add("hidden");
    _newKeyValue.textContent = result.api_key || "—";
    _keyCreatedModal.classList.remove("hidden");
    if (_isDemo) {
      DEMO_KEYS.push({
        client_name: clientName,
        environment,
        key_prefix: result.api_key.slice(0, 12) + "...",
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
    const isActive = key.is_active !== false;
    if (!isActive) tr.classList.add("row-inactive");
    const actionCell = isActive
      ? `<button class="btn-danger btn-sm">Revoke</button>`
      : `<span class="badge badge-revoked">Revoked</span>`;
    tr.innerHTML = `
      <td>${Helpers.esc(key.client_name || "—")}</td>
      <td>${Helpers.esc(key.environment || "—")}</td>
      <td><code>${key.key_prefix ? Helpers.esc(key.key_prefix) + "…" : "—"}</code></td>
      <td>${Helpers.formatDate(key.created_at)}</td>
      <td>${key.last_used ? Helpers.formatDate(key.last_used) : "—"}</td>
      <td>${actionCell}</td>
    `;
    if (isActive) {
      tr.querySelector("button").addEventListener("click", () => {
        if (_isDemo) { tr.remove(); if (!_tbody.children.length) _noKeys.classList.remove("hidden"); }
        else openRevokeModal(key.key_prefix);
      });
    }
    _tbody.appendChild(tr);
  }
}

export async function load() {
  try {
    const includeInactive = _showInactiveToggle?.checked || false;
    const data = await KeysService.list({ includeInactive });
    render(data.keys || []);
  } catch (e) {
    _tbody.innerHTML = "";
    _noKeys.textContent = e.message;
    _noKeys.classList.remove("hidden");
  }
}

