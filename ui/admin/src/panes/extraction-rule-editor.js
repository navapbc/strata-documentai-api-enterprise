/**
 * Blueprint editor pane - renders fields for the active document type.
 * Allows toggling required/optional/excluded per field.
 * Uses the global TenantContext for tenant selection.
 */
import * as Store from "../state/blueprint-store.js";
import * as RulesService from "../services/rules.js";
import * as TenantContext from "../utils/tenant-context.js";
import * as Toast from "../utils/toast.js";
import { h } from "../utils/dom.js";

let _root = null;
let _storeUnsub = null;
let _tenantUnsub = null;
let _lastRulesKey = null;

// Per-doc-type dirty state for the all-blueprints view
// { [docType]: { rules: {}, ruleExists: bool } }
let _localRules = {};

export function mount(root) {
  _root = root;
  root.replaceChildren();

  const tenantId = TenantContext.getTenantId();
  if (tenantId) {
    Store.set({ tenantId });
    loadAllRules(tenantId);
  }

  _tenantUnsub = TenantContext.onChange((tid) => {
    Store.set({
      tenantId: tid || null,
      rules: {},
      ruleExists: false,
      dirty: false,
      allRules: [],
    });
    _lastRulesKey = null;
    _localRules = {};
    if (tid) loadAllRules(tid);
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

async function loadAllRules(tenantId) {
  try {
    const data = await RulesService.list(tenantId);
    Store.set({ allRules: data.rules || [] });
  } catch {
    Store.set({ allRules: [] });
  }
}

async function loadRules(tenantId, docType) {
  if (!tenantId || !docType) return;
  try {
    const data = await RulesService.get(tenantId, docType);
    const rule = data.rules?.[0];
    const ruleExists = (data.rules?.length ?? 0) > 0;
    const rules = {};
    for (const f of rule?.requiredFields || []) rules[f] = "required";
    for (const f of rule?.optionalFields || []) rules[f] = "optional";
    Store.set({ rules, ruleExists });
  } catch {
    Store.set({ rules: {}, ruleExists: false });
  }
}

function makeToggle(radioName, fieldName, value, label, cls, currentState, editable, onChange) {
  const input = h("input", { type: "radio", name: radioName, value });
  if (editable && currentState === value) input.checked = true;
  if (!editable) input.disabled = true;
  input.addEventListener("change", () => onChange(fieldName, value));
  return h(
    "label",
    { className: "toggle-label" },
    input,
    h("span", { className: `toggle-badge ${cls}` }, label),
  );
}

function renderDocTypeSection(
  docType,
  fields,
  rules,
  ruleExists,
  editable,
  onChange,
  onSave,
  onDiscard,
  dirty,
) {
  const section = h("div", { className: "doc-type-section" });

  const header = h(
    "div",
    { className: "fields-list-header-row" },
    h("h3", { className: "fields-list-header" }, docType),
  );

  if (editable) {
    const saveBtn = h("button", { className: "btn-primary btn-sm" }, "Save");
    const discardBtn = h("button", { className: "btn-secondary btn-sm" }, "Discard");
    if (!dirty) {
      saveBtn.style.visibility = "hidden";
      discardBtn.style.visibility = "hidden";
    }
    saveBtn.addEventListener("click", () => onSave(docType));
    discardBtn.addEventListener("click", () => onDiscard(docType));
    header.appendChild(discardBtn);
    header.appendChild(saveBtn);
  }

  section.appendChild(header);

  for (const field of fields) {
    const defaultState = ruleExists ? "excluded" : "optional";
    const fieldState = rules[field.name] || defaultState;
    const radioName = `rule-${docType}-${field.name}`;

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
        editable
          ? { className: "field-toggles" }
          : { className: "field-toggles", title: "Select a tenant to edit extraction rules" },
        makeToggle(
          radioName,
          field.name,
          "required",
          "Required",
          "toggle-required",
          fieldState,
          editable,
          onChange,
        ),
        makeToggle(
          radioName,
          field.name,
          "optional",
          "Optional",
          "toggle-optional",
          fieldState,
          editable,
          onChange,
        ),
        makeToggle(
          radioName,
          field.name,
          "excluded",
          "Excluded",
          "toggle-excluded",
          fieldState,
          editable,
          onChange,
        ),
      ),
    );
    section.appendChild(row);
  }

  return section;
}

function render(state) {
  if (!_root) return;
  const { schemas, schemasLoading, activeDocType, rules, dirty, tenantId, allRules = [] } = state;

  if (!activeDocType) {
    if (schemasLoading) {
      _root.replaceChildren(h("p", { className: "empty-state" }, "Loading…"));
      return;
    }
    if (!Object.keys(schemas).length) {
      _root.replaceChildren(h("p", { className: "empty-state" }, "No document types found."));
      return;
    }
    const fieldsList = h("div", { id: "bp-fields-list", className: "fields-list" });
    for (const [docType, fields] of Object.entries(schemas).sort(([a], [b]) =>
      a.localeCompare(b),
    )) {
      const docRule = allRules.find((r) => (r.documentType || r.document_type) === docType);
      const baseRules = {};
      for (const f of docRule?.requiredFields || docRule?.required_fields || [])
        baseRules[f] = "required";
      for (const f of docRule?.optionalFields || docRule?.optional_fields || [])
        baseRules[f] = "optional";
      const ruleExists = !!docRule;

      if (!_localRules[docType] || !_localRules[docType].dirty) {
        _localRules[docType] = { rules: baseRules, ruleExists, dirty: false };
      }

      const local = _localRules[docType];

      const section = renderDocTypeSection(
        docType,
        fields,
        local.rules,
        local.ruleExists,
        !!tenantId,
        (fieldName, value) =>
          onChangeLocal(fieldsList, docType, fields, allRules, tenantId, fieldName, value),
        (dt) => saveDocType(dt),
        (dt) => discardDocType(dt, baseRules, ruleExists),
        local.dirty,
      );
      section.dataset.docType = docType;
      fieldsList.appendChild(section);
    }
    _root.replaceChildren(fieldsList);
    return;
  }

  // Single doc type view
  const editable = !!tenantId;
  const fields = schemas[activeDocType] || [];
  if (fields.length === 0) {
    _root.replaceChildren(
      h("p", { className: "empty-state" }, schemasLoading ? "Loading…" : "No fields defined."),
    );
    return;
  }

  const fieldsList = h("div", { id: "bp-fields-list", className: "fields-list" });
  fieldsList.appendChild(
    renderDocTypeSection(
      activeDocType,
      fields,
      rules,
      state.ruleExists,
      editable,
      (fieldName, value) => {
        const updated = { ...Store.get().rules };
        if (value === "excluded") delete updated[fieldName];
        else updated[fieldName] = value;
        Store.set({ rules: updated, dirty: true });
      },
      () => saveRules(),
      () => discardChanges(),
      dirty,
    ),
  );

  const rulesKey = `${tenantId}:${activeDocType}`;
  if (tenantId && activeDocType && rulesKey !== _lastRulesKey) {
    _lastRulesKey = rulesKey;
    loadRules(tenantId, activeDocType);
  }
  _root.replaceChildren(fieldsList);
}

function onChangeLocal(fieldsList, docType, fields, allRules, tenantId, fieldName, value) {
  const updated = { ...(_localRules[docType]?.rules || {}) };
  updated[fieldName] = value;
  _localRules[docType] = { ...(_localRules[docType] || {}), rules: updated, dirty: true };
  const docRule = allRules.find((r) => (r.documentType || r.document_type) === docType);
  const baseRules = {};
  for (const f of docRule?.requiredFields || docRule?.required_fields || [])
    baseRules[f] = "required";
  for (const f of docRule?.optionalFields || docRule?.optional_fields || [])
    baseRules[f] = "optional";
  const ruleExists = !!docRule;
  const existing = fieldsList.querySelector(`[data-doc-type="${docType}"]`);
  const next = renderDocTypeSection(
    docType,
    fields,
    updated,
    ruleExists,
    !!tenantId,
    (fn, v) => onChangeLocal(fieldsList, docType, fields, allRules, tenantId, fn, v),
    (dt) => saveDocType(dt),
    (dt) => discardDocType(dt, baseRules, ruleExists),
    true,
  );
  next.dataset.docType = docType;
  if (existing) fieldsList.replaceChild(next, existing);
}

async function saveDocType(docType) {
  const { tenantId } = Store.get();
  if (!tenantId) return;
  const local = _localRules[docType];
  if (!local) return;

  const requiredFields = [];
  const optionalFields = [];
  for (const [field, rule] of Object.entries(local.rules)) {
    if (rule === "required") requiredFields.push(field);
    else if (rule === "optional") optionalFields.push(field);
  }

  try {
    await RulesService.put(tenantId, docType, requiredFields, optionalFields);
    _localRules[docType] = { ...local, dirty: false };
    Toast.show(`${docType} rules saved`);
    // Refresh allRules so re-renders are consistent
    loadAllRules(tenantId);
  } catch (e) {
    Toast.show(`Failed to save: ${e.message}`);
  }
}

function discardDocType(docType, baseRules, ruleExists) {
  _localRules[docType] = { rules: baseRules, ruleExists, dirty: false };
  // Trigger re-render via store no-op
  Store.set({});
}

async function saveRules() {
  const { tenantId, activeDocType, rules, dirty } = Store.get();
  if (!tenantId || !activeDocType || !dirty) return;

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
