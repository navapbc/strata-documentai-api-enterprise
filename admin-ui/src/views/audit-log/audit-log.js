import * as AuditLogService from "../../services/audit-log.js";
import * as TenantContext from "../../utils/tenant-context.js";
import * as Helpers from "../../utils/helpers.js";
import { h } from "../../utils/dom.js";
import { tpl } from "../../utils/tpl.js";
import html from "./audit-log.html";

const tmpl = tpl(html);

let _root, _tbody, _noEvents, _refreshBtn, _nextBtn, _prevBtn;
let _actionFilter, _startDate, _endDate;
let _cursor = null;
let _cursorStack = [];
let _actionsLoaded = false;
let _tenantUnsub = null;

export function mount(root) {
  _root = root;
  root.replaceChildren(tmpl());

  // Inject actions into shared header
  _actionFilter = h(
    "select",
    { className: "tenant-select", id: "audit-action-filter" },
    h("option", { value: "" }, "All actions"),
  );
  _startDate = h("input", { type: "date", id: "audit-start-date", title: "Start date" });
  _endDate = h("input", { type: "date", id: "audit-end-date", title: "End date" });
  _refreshBtn = h("button", { className: "btn-secondary" }, "Refresh");
  Helpers.setViewActions(_actionFilter, _startDate, _endDate, _refreshBtn);

  _tbody = root.querySelector("#audit-tbody");
  _noEvents = root.querySelector("#no-audit-events");
  _nextBtn = root.querySelector("#audit-next-btn");
  _prevBtn = root.querySelector("#audit-prev-btn");

  _refreshBtn.addEventListener("click", () => {
    resetPagination();
    load();
  });
  _nextBtn.addEventListener("click", loadNext);
  _prevBtn.addEventListener("click", loadPrev);
  _actionFilter.addEventListener("change", () => {
    resetPagination();
    load();
  });
  _startDate.addEventListener("change", () => {
    resetPagination();
    load();
  });
  _endDate.addEventListener("change", () => {
    resetPagination();
    load();
  });

  _tenantUnsub = TenantContext.onChange(() => {
    resetPagination();
    load();
  });
  loadActions();
  load();
}

export function unmount(root) {
  if (_tenantUnsub) {
    _tenantUnsub();
    _tenantUnsub = null;
  }
  root.replaceChildren();
}

function resetPagination() {
  _cursor = null;
  _cursorStack = [];
}

async function loadActions() {
  if (_actionsLoaded) return;
  try {
    const resp = await AuditLogService.listActions();
    _actionFilter.innerHTML = '<option value="">All actions</option>';
    for (const action of resp.actions || []) {
      const opt = document.createElement("option");
      opt.value = action;
      opt.textContent = action;
      _actionFilter.appendChild(opt);
    }
    _actionsLoaded = true;
  } catch {
    // leave dropdown with just "All actions"
  }
}

export async function load() {
  Helpers.showLoading(_tbody, _noEvents);
  try {
    const resp = await AuditLogService.list({
      tenantId: TenantContext.getTenantId(),
      action: _actionFilter.value || undefined,
      startDate: _startDate.value || undefined,
      endDate: _endDate.value || undefined,
      limit: 50,
      cursor: _cursor || undefined,
    });
    render(resp.events || []);
    _nextBtn.disabled = !resp.nextCursor;
    _nextBtn.dataset.cursor = resp.nextCursor || "";
    _prevBtn.disabled = _cursorStack.length === 0;
  } catch (e) {
    _tbody.innerHTML = "";
    _noEvents.textContent = e.message;
    _noEvents.classList.remove("hidden");
  }
}

function loadNext() {
  const next = _nextBtn.dataset.cursor;
  if (!next) return;
  _cursorStack.push(_cursor);
  _cursor = next;
  load();
}

function loadPrev() {
  if (_cursorStack.length === 0) return;
  _cursor = _cursorStack.pop();
  load();
}

function render(events) {
  _tbody.innerHTML = "";
  if (events.length === 0) {
    _noEvents.classList.remove("hidden");
    return;
  }
  _noEvents.classList.add("hidden");
  for (const ev of events) {
    const tr = h(
      "tr",
      null,
      h("td", null, Helpers.formatDate(ev.timestamp)),
      h("td", null, ev.actorEmail || "-"),
      h("td", null, h("code", null, ev.action || "-")),
      h("td", null, ev.targetType || "-"),
      h("td", null, ev.targetId || "-"),
      h("td", null, ev.tenantId || "-"),
      h("td", { className: "audit-meta" }, formatMeta(ev.metadata)),
    );
    _tbody.appendChild(tr);
  }
}

function formatMeta(meta) {
  if (!meta || Object.keys(meta).length === 0) return "-";
  return Helpers.esc(JSON.stringify(meta));
}
