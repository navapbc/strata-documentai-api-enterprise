/**
 * Blueprints screen - composes blueprint-list, blueprint-editor, and field-search panes.
 * Shared state lives in js/state/blueprint-store.js.
 */
import * as Store from "../../state/blueprint-store.js";
import * as SchemasService from "../../services/schemas.js";
import * as BlueprintList from "../../panes/blueprint-list.js";
import * as ExtractionRuleEditor from "../../panes/extraction-rule-editor.js";
import * as FieldSearch from "../../panes/field-search.js";
import * as Toast from "../../utils/toast.js";
import * as TenantContext from "../../utils/tenant-context.js";
import { tpl } from "../../utils/tpl.js";
import html from "./extraction-rules.html";

const tmpl = tpl(html);

let _unsubs = [];

export function mount(root) {
  root.replaceChildren(tmpl());

  TenantContext.mountSelect(root.querySelector("#tenant-select"), { placeholder: "Select Tenant" });

  _unsubs = [
    BlueprintList.mount(root.querySelector("#bp-list-pane")),
    ExtractionRuleEditor.mount(root.querySelector("#extraction-rule-editor-pane")),
    FieldSearch.mount(root.querySelector("#bp-search-pane")),
    Store.subscribe(() => {}),
  ];

  loadSchemas();

  // Restore active blueprint from hash (e.g. #extraction-rules/pay_stub)
  const hashParts = location.hash.replace("#", "").split("/");
  if (hashParts[1]) {
    Store.set({ activeDocType: decodeURIComponent(hashParts[1]) });
  }
}

export function unmount(root) {
  const tenantSelect = root.querySelector("#tenant-select");
  if (tenantSelect) TenantContext.unmountSelect(tenantSelect);
  _unsubs.forEach((u) => u && u());
  _unsubs = [];
  Store.reset();
  root.replaceChildren();
}

export function hasUnsavedChanges() {
  return Store.get().dirty;
}

export function getActiveDocType() {
  return Store.get().activeDocType;
}

async function loadSchemas() {
  if (Object.keys(Store.get().schemas).length > 0) return;
  try {
    const data = await SchemasService.getAllFields();
    Store.set({ schemas: SchemasService.groupFieldsByDocType(data), schemasLoading: false });
  } catch (e) {
    Store.set({ schemasLoading: false });
    Toast.show(`Failed to load schemas: ${e.message}`);
  }
}

// Re-export for sidebar population (used by main.js dashboard setup)
export function populateSidebar() {
  // No-op - the list pane auto-renders from store subscription
}

export function select(docType) {
  Store.set({ activeDocType: docType });
}

export async function load() {
  await loadSchemas();
}
