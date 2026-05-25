import * as AuditLogService from "../services/audit-log.js";
import * as TenantContext from "../utils/tenant-context.js";
import * as Helpers from "../utils/helpers.js";
import * as Toast from "../utils/toast.js";

let _tbody, _noEvents, _refreshBtn, _nextBtn, _prevBtn;
let _actionFilter, _startDate, _endDate;
let _cursor = null;
let _cursorStack = []; // for "previous" navigation

export function init() {
  _tbody = document.getElementById("audit-tbody");
  _noEvents = document.getElementById("no-audit-events");
  _refreshBtn = document.getElementById("refresh-audit-btn");
  _nextBtn = document.getElementById("audit-next-btn");
  _prevBtn = document.getElementById("audit-prev-btn");
  _actionFilter = document.getElementById("audit-action-filter");
  _startDate = document.getElementById("audit-start-date");
  _endDate = document.getElementById("audit-end-date");

  _refreshBtn.addEventListener("click", () => { resetPagination(); load(); });
  _nextBtn.addEventListener("click", loadNext);
  _prevBtn.addEventListener("click", loadPrev);
  _actionFilter.addEventListener("change", () => { resetPagination(); load(); });
  _startDate.addEventListener("change", () => { resetPagination(); load(); });
  _endDate.addEventListener("change", () => { resetPagination(); load(); });

  TenantContext.onChange(() => { resetPagination(); load(); });
}

function resetPagination() {
  _cursor = null;
  _cursorStack = [];
}

let _actionsLoaded = false;

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
  await loadActions();
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
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${Helpers.formatDate(ev.timestamp)}</td>
      <td>${Helpers.esc(ev.actorEmail)}</td>
      <td><code>${Helpers.esc(ev.action)}</code></td>
      <td>${Helpers.esc(ev.targetType)}</td>
      <td>${Helpers.esc(ev.targetId)}</td>
      <td>${Helpers.esc(ev.tenantId)}</td>
      <td class="audit-meta">${formatMeta(ev.metadata)}</td>
    `;
    _tbody.appendChild(tr);
  }
}

function formatMeta(meta) {
  if (!meta || Object.keys(meta).length === 0) return "—";
  return Helpers.esc(JSON.stringify(meta));
}
