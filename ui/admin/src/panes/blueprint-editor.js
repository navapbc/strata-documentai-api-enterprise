/**
 * Blueprint editor pane - renders fields for the active document type.
 * Allows toggling required/optional/excluded per field.
 * Uses the global TenantContext for tenant selection.
 */
import * as Store from "../state/blueprint-store.js";
import * as RulesService from "../services/rules.js";
import * as TenantContext from "../utils/tenant-context.js";
import * as Helpers from "../utils/helpers.js";
import * as Toast from "../utils/toast.js";
import { h } from "../utils/dom.js";

let _root = null;
let _storeUnsub = null;
let _tenantUnsub = null;
let _saveBtn = null;
let _discardBtn = null;
let _lastRulesKey = null;

export function mount(root) {
  _root = root;
  root.innerHTML = `
    <div class="content-header">
      <h2 id="bp-editor-title">Select a blueprint</h2>
      <div class="content-actions">
        <button id="bp-discard-btn" class="btn-secondary hidden">Discard</button>
        <button id="bp-save-btn" class="btn-primary" disabled>Save Rules</button>
      </div>
    </div>
    <div id="bp-fields-list" class="fields-list"></div>
  `;

  _saveBtn = root.querySelector("#bp-save-btn");
  _discardBtn = root.querySelector("#bp-discard-btn");

  _saveBtn.addEventListener("click", saveRules);
  _discardBtn.addEventListener("click", discardChanges);

  // Use global tenant context
  const tenantId = TenantContext.getTenantId();
  if (tenantId) Store.set({ tenantId });

  _tenantUnsub = TenantContext.onChange((tid) => {
    Store.set({ tenantId: tid || null, rules: {}, dirty: false });
    _lastRulesKey = null;
  });

  _storeUnsub = Store.subscribe(render);
  render(Store.get());
  return unmount;
}

function unmount() {
  if (_storeUnsub) {
    _storeUnsub();
    _storeUnsub = null;
  }
  if (_tenantUnsub) {
    _tenantUnsub();
    _tenantUnsub = null;
  }
  if (_root) _root.replaceChildren();
}

async function loadRules(tenantId, docType) {
  if (!tenantId || !docType) return;
  try {
    const data = await RulesService.get(tenantId, docType);
    const rule = data.rules?.[0] || {};
    const rules = {};
    for (const f of rule.requiredFields || []) rules[f] = "required";
    for (const f of rule.optionalFields || []) rules[f] = "optional";
    Store.set({ rules });
  } catch {
    Store.set({ rules: {} });
  }
}

function render(state) {
  if (!_root) return;
  const { schemas, activeDocType, rules, dirty, tenantId } = state;
  const title = _root.querySelector("#bp-editor-title");
  const fieldsList = _root.querySelector("#bp-fields-list");

  if (!title || !fieldsList) return;

  title.textContent = activeDocType || "Select a blueprint";
  _saveBtn.disabled = !dirty || !tenantId;
  _discardBtn.classList.toggle("hidden", !dirty);

  if (!activeDocType) {
    fieldsList.replaceChildren(
      h("p", { className: "empty-state" }, "Select a document type from the list."),
    );
    return;
  }

  const fields = schemas[activeDocType] || [];
  if (fields.length === 0) {
    fieldsList.replaceChildren(h("p", { className: "empty-state" }, "No fields defined."));
    return;
  }

  fieldsList.replaceChildren();
  for (const field of fields) {
    const fieldState = rules[field.name] || "excluded";
    const radioName = `rule-${field.name}`;

    function makeToggle(value, label, cls) {
      const input = h("input", { type: "radio", name: radioName, value });
      if (fieldState === value) input.checked = true;
      input.addEventListener("change", () => {
        const updated = { ...Store.get().rules };
        if (value === "excluded") delete updated[field.name];
        else updated[field.name] = value;
        Store.set({ rules: updated, dirty: true });
      });
      return h(
        "label",
        { className: "toggle-label" },
        input,
        h("span", { className: `toggle-badge ${cls}` }, label),
      );
    }

    const row = h(
      "div",
      { className: "field-row" },
      h(
        "div",
        { className: "field-info" },
        h("span", { className: "field-name" }, field.name),
        h("span", { className: "field-type" }, field.type || "string"),
      ),
      h(
        "div",
        { className: "field-toggles" },
        makeToggle("required", "Required", "toggle-required"),
        makeToggle("optional", "Optional", "toggle-optional"),
        makeToggle("excluded", "Excluded", "toggle-excluded"),
      ),
    );
    fieldsList.appendChild(row);
  }

  // Load rules when docType or tenant changes
  const rulesKey = `${tenantId}:${activeDocType}`;
  if (tenantId && activeDocType && rulesKey !== _lastRulesKey) {
    _lastRulesKey = rulesKey;
    loadRules(tenantId, activeDocType);
  }
}

async function saveRules() {
  const { tenantId, activeDocType, rules } = Store.get();
  if (!tenantId || !activeDocType) return;

  const requiredFields = [];
  const optionalFields = [];
  for (const [field, rule] of Object.entries(rules)) {
    if (rule === "required") requiredFields.push(field);
    else if (rule === "optional") optionalFields.push(field);
  }

  try {
    await RulesService.put(tenantId, activeDocType, requiredFields, optionalFields);
    Store.set({ dirty: false });
    Toast.show("Rules saved");
  } catch (e) {
    Toast.show(`Failed to save: ${e.message}`);
  }
}

function discardChanges() {
  const { tenantId, activeDocType } = Store.get();
  Store.set({ dirty: false });
  _lastRulesKey = null;
  if (tenantId && activeDocType) loadRules(tenantId, activeDocType);
  Toast.show("Changes discarded");
}
