import * as AuditLogService from "../../services/audit-log.js";
import * as TenantContext from "../../utils/tenant-context.js";
import * as Helpers from "../../utils/helpers.js";
import { localDateToUtcStart, localDateToUtcEnd } from "../../utils/helpers.js";
const PAGE_SIZE = 50;
import { h } from "../../utils/dom.js";
import { tpl } from "../../utils/tpl.js";
import html from "./audit-log.html";

const tmpl = tpl(html);

let _root, _tbody, _table, _noEvents, _nextBtn, _prevBtn, _pagination;
let _actionFilter, _actorFilter;
let _timeframeSelect, _customRange, _startDate, _endDate, _loadBtn;
let _pageIndicator;
let _cursor = null;
let _cursorStack = [];
let _pageNum = 1;
let _actionsLoaded = false;
let _tenantUnsub = null;

export function mount(root) {
  _root = root;
  root.replaceChildren(tmpl());

  _actionFilter = root.querySelector("#audit-action-filter");
  _actorFilter = root.querySelector("#audit-actor-filter");
  _timeframeSelect = root.querySelector("#audit-timeframe");
  _customRange = root.querySelector("#audit-custom-range");
  _startDate = root.querySelector("#audit-start-date");
  _endDate = root.querySelector("#audit-end-date");
  _loadBtn = root.querySelector("#audit-load-btn");
  Helpers.setViewActions();

  _tbody = root.querySelector("#audit-tbody");
  _table = root.querySelector("#audit-table");
  _noEvents = root.querySelector("#no-audit-events");
  _nextBtn = root.querySelector("#audit-next-btn");
  _prevBtn = root.querySelector("#audit-prev-btn");
  _pageIndicator = root.querySelector("#audit-page-indicator");
  _pagination = root.querySelector("#audit-pagination");

  const today = new Date().toISOString().slice(0, 10);
  _startDate.max = today;
  _endDate.max = today;

  _timeframeSelect.addEventListener("change", () => {
    if (_timeframeSelect.value === "custom") {
      _customRange.classList.remove("hidden");
    } else {
      _customRange.classList.add("hidden");
      resetPagination();
      load();
    }
  });
  _loadBtn.addEventListener("click", () => {
    resetPagination();
    load();
  });
  _nextBtn.addEventListener("click", loadNext);
  _prevBtn.addEventListener("click", loadPrev);
  _actionFilter.addEventListener("change", () => {
    resetPagination();
    load();
  });
  _actorFilter.addEventListener("change", () => {
    resetPagination();
    load();
  });

  _tenantUnsub = TenantContext.onChange(async () => {
    resetPagination();
    // Rebuild the actor dropdown for the new tenant before loading events -
    // otherwise load() reads the previous tenant's stale actor selection.
    await loadActors();
    load();
  });
  loadActions();
  loadActors();
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
  _pageNum = 1;
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

async function loadActors() {
  try {
    const resp = await AuditLogService.listActors({ tenantId: TenantContext.getTenantId() });
    const current = _actorFilter.value;
    _actorFilter.innerHTML = '<option value="">All actors</option>';
    for (const actor of resp.actors || []) {
      const opt = document.createElement("option");
      opt.value = actor;
      opt.textContent = actor;
      if (actor === current) opt.selected = true;
      _actorFilter.appendChild(opt);
    }
  } catch {
    // leave dropdown with just "All actors"
  }
}

function _getDateRange() {
  const val = _timeframeSelect.value;
  if (val === "custom") {
    return {
      startDate: _startDate.value ? localDateToUtcStart(_startDate.value) : undefined,
      endDate: _endDate.value ? localDateToUtcEnd(_endDate.value) : undefined,
    };
  }
  if (val === "1") {
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);
    const d = yesterday.toISOString().slice(0, 10);
    return { startDate: localDateToUtcStart(d), endDate: localDateToUtcEnd(d) };
  }
  const end = new Date();
  const start = new Date();
  start.setDate(end.getDate() - parseInt(val));
  return {
    startDate: localDateToUtcStart(start.toISOString().slice(0, 10)),
    endDate: localDateToUtcEnd(end.toISOString().slice(0, 10)),
  };
}

export async function load() {
  _table.classList.add("hidden");
  _noEvents.textContent = "Loading…";
  _noEvents.classList.remove("hidden");
  const { startDate, endDate } = _getDateRange();
  try {
    const resp = await AuditLogService.list({
      tenantId: TenantContext.getTenantId(),
      action: _actionFilter.value || undefined,
      actorEmail: _actorFilter.value || undefined,
      startDate,
      endDate,
      limit: PAGE_SIZE,
      cursor: _cursor || undefined,
    });
    const events = resp.events || [];
    render(events);
    // Disable Next if no cursor returned OR if fewer results than page size (definitely last page)
    const hasMore = !!resp.nextCursor && events.length >= PAGE_SIZE;
    _nextBtn.disabled = !hasMore;
    _nextBtn.dataset.cursor = resp.nextCursor || "";
    _prevBtn.disabled = _cursorStack.length === 0;
    const hasPagination = hasMore || _cursorStack.length > 0;
    _pagination.classList.toggle("hidden", !hasPagination);
    if (_pageIndicator) _pageIndicator.textContent = events.length > 0 ? `Page ${_pageNum}` : "";
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
  _pageNum++;
  load();
}

function loadPrev() {
  if (_cursorStack.length === 0) return;
  _cursor = _cursorStack.pop();
  _pageNum--;
  load();
}

function render(events) {
  _tbody.innerHTML = "";
  if (events.length === 0) {
    _table.classList.add("hidden");
    _noEvents.textContent = "No audit events found.";
    _noEvents.classList.remove("hidden");
    return;
  }
  _table.classList.remove("hidden");
  _noEvents.classList.add("hidden");
  const rowOffset = (_pageNum - 1) * PAGE_SIZE;
  for (const [i, ev] of events.entries()) {
    const hasDetail =
      ev.targetType ||
      ev.targetId ||
      ev.tenantId ||
      (ev.metadata && Object.keys(ev.metadata).length > 0);
    const detailTr = h(
      "tr",
      { className: "audit-detail-row hidden" },
      h("td", { className: "audit-detail-spacer" }),
      h(
        "td",
        { colSpan: "3" },
        h(
          "div",
          { className: "audit-detail-cell" },
          ...(ev.targetType
            ? [
                h(
                  "span",
                  { className: "audit-detail-item" },
                  h("span", { className: "audit-detail-key" }, "Target Type"),
                  ev.targetType,
                ),
              ]
            : []),
          ...(ev.targetId
            ? [
                h(
                  "span",
                  { className: "audit-detail-item" },
                  h("span", { className: "audit-detail-key" }, "Target ID"),
                  ev.targetId,
                ),
              ]
            : []),
          ...(ev.tenantId
            ? [
                h(
                  "span",
                  { className: "audit-detail-item" },
                  h("span", { className: "audit-detail-key" }, "Tenant"),
                  ev.tenantId,
                ),
              ]
            : []),
          ...(ev.metadata && Object.keys(ev.metadata).length > 0
            ? [
                h(
                  "span",
                  { className: "audit-detail-item" },
                  h("span", { className: "audit-detail-key" }, "Metadata"),
                  JSON.stringify(ev.metadata),
                ),
              ]
            : []),
        ),
      ),
    );
    const tr = h(
      "tr",
      { className: hasDetail ? "audit-row-expandable" : "" },
      h(
        "td",
        { style: "color:#9ca3af;font-size:0.75rem;text-align:right;" },
        String(rowOffset + i + 1),
        hasDetail ? h("span", { className: "audit-expand-cell" }, "›") : "",
      ),
      h("td", null, Helpers.formatDateTime(ev.timestamp)),
      h("td", null, ev.actorEmail || "-"),
      h("td", null, ev.action || "-"),
    );
    if (hasDetail) {
      tr.addEventListener("click", () => {
        const open = detailTr.classList.toggle("hidden");
        tr.querySelector(".audit-expand-cell").classList.toggle("open", !open);
      });
    }
    _tbody.appendChild(tr);
    _tbody.appendChild(detailTr);
  }
}
