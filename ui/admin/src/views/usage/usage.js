import * as UsageService from "../../services/usage.js";
import * as TenantContext from "../../utils/tenant-context.js";
import * as Toast from "../../utils/toast.js";
import { tpl } from "../../utils/tpl.js";
import { h } from "../../utils/dom.js";
import html from "./usage.html";

const tmpl = tpl(html);

let _root;
let _yearSelect, _monthSelect, _granularitySelect, _downloadBtn, _tableContainer, _empty;
let _currentData = [];
let _currentGranularity = "monthly";
let _tenantUnsub = null;
let _loadId = 0;

export function mount(root) {
  _root = root;
  root.replaceChildren(tmpl());

  _yearSelect = root.querySelector("#usage-year");
  _monthSelect = root.querySelector("#usage-month");
  _granularitySelect = root.querySelector("#usage-granularity");
  _downloadBtn = root.querySelector("#usage-download-btn");
  _tableContainer = root.querySelector("#usage-table-container");
  _empty = root.querySelector("#usage-empty");

  // Populate year select (current year back to 2025)
  const now = new Date();
  const currentYear = now.getFullYear();
  for (let y = currentYear; y >= 2025; y--) {
    const opt = document.createElement("option");
    opt.value = String(y);
    opt.textContent = String(y);
    _yearSelect.appendChild(opt);
  }
  _yearSelect.value = String(currentYear);
  _monthSelect.value = String(now.getMonth() + 1).padStart(2, "0");

  _yearSelect.addEventListener("change", load);
  _monthSelect.addEventListener("change", load);
  _granularitySelect.addEventListener("change", load);
  _downloadBtn.addEventListener("click", downloadCsv);

  _tenantUnsub = TenantContext.onChange(() => load());

  load();
}

export function unmount(_root) {
  if (_tenantUnsub) {
    _tenantUnsub();
    _tenantUnsub = null;
  }
  _root = null;
  _currentData = [];
}

async function load() {
  const month = `${_yearSelect.value}-${_monthSelect.value}`;
  const tenantId = TenantContext.getTenantId();
  _currentGranularity = _granularitySelect.value;
  const thisLoad = ++_loadId;

  _empty.textContent = "Loading...";
  _empty.classList.remove("hidden");
  _tableContainer.querySelectorAll("table").forEach((t) => t.remove());

  try {
    const resp = await UsageService.get({ month, granularity: _currentGranularity, tenantId });

    if (thisLoad !== _loadId) return;

    // Daily is intentionally parked: the granularity <option> is commented out in
    // usage.html because daily reads from the metrics aggregator (not Athena) and may
    // not reconcile with monthly totals. This branch + _fillDailyGaps stay so re-enabling
    // is a one-line uncomment once the usage_report job emits deduped daily files.
    if (_currentGranularity === "daily") {
      _currentData = _fillDailyGaps(month, resp.days || []);
    } else {
      _currentData = resp.tenants || [];
    }

    renderTable();
  } catch (e) {
    _empty.textContent = `Failed to load: ${e.message}`;
    Toast.show(`Usage load failed: ${e.message}`);
  }
}

function renderTable() {
  _tableContainer.querySelectorAll("table").forEach((t) => t.remove());

  if (!_currentData.length) {
    _empty.textContent = "No data available for this period.";
    _empty.classList.remove("hidden");
    return;
  }

  _empty.classList.add("hidden");

  const columns =
    _currentGranularity === "daily"
      ? [
          { key: "date", label: "Date" },
          { key: "totalRecords", label: "Documents Processed" },
          { key: "totalBdaPages", label: "Pages Processed" },
          { key: "totalFileSizeBytes", label: "Total Size" },
          { key: "totalBedrockInputTokens", label: "Input Tokens" },
          { key: "totalBedrockOutputTokens", label: "Output Tokens" },
        ]
      : [
          { key: "tenantId", label: "Tenant" },
          { key: "totalRecords", label: "Documents Processed" },
          { key: "totalBdaPages", label: "Pages Processed" },
          { key: "totalFileSizeBytes", label: "Total Size" },
          { key: "totalBedrockInputTokens", label: "Input Tokens" },
          { key: "totalBedrockOutputTokens", label: "Output Tokens" },
        ];

  const thead = h("thead", {}, h("tr", {}, ...columns.map((col) => h("th", {}, col.label))));

  const tbody = h(
    "tbody",
    {},
    ..._currentData.map((row) =>
      h("tr", {}, ...columns.map((col) => h("td", {}, formatCell(col.key, row[col.key])))),
    ),
  );

  let tfoot = null;
  if (_currentData.length > 1) {
    const totals = {};
    for (const col of columns) {
      if (col.key === "date" || col.key === "tenantId") {
        totals[col.key] = "Total";
      } else {
        totals[col.key] = _currentData.reduce((sum, row) => sum + (row[col.key] || 0), 0);
      }
    }
    tfoot = h(
      "tfoot",
      {},
      h(
        "tr",
        { className: "totals-row" },
        ...columns.map((col) => h("td", {}, formatCell(col.key, totals[col.key]))),
      ),
    );
  }

  const table = h(
    "table",
    { className: "detail-table usage-table" },
    thead,
    tbody,
    ...(tfoot ? [tfoot] : []),
  );
  _tableContainer.appendChild(table);
}

function formatCell(key, value) {
  if (value == null) return "-";
  if (key === "totalFileSizeBytes") {
    return `${(value / 1024 / 1024).toFixed(1)} MB`;
  }
  if (typeof value === "number") {
    return value.toLocaleString();
  }
  return String(value);
}

export function _fillDailyGaps(month, days) {
  const year = parseInt(month.slice(0, 4), 10);
  const mo = parseInt(month.slice(5, 7), 10);
  const daysInMonth = new Date(year, mo, 0).getDate();

  const today = new Date();
  const isCurrentMonth = today.getFullYear() === year && today.getMonth() + 1 === mo;
  const lastDay = isCurrentMonth ? today.getDate() : daysInMonth;

  const byDate = {};
  for (const d of days) byDate[d.date] = d;

  const result = [];
  for (let day = 1; day <= lastDay; day++) {
    const date = `${month}-${String(day).padStart(2, "0")}`;
    result.push(
      byDate[date] || {
        date,
        totalRecords: 0,
        totalBdaPages: 0,
        totalFileSizeBytes: 0,
        totalBedrockInputTokens: 0,
        totalBedrockOutputTokens: 0,
      },
    );
  }
  return result;
}

function downloadCsv() {
  if (!_currentData.length) return;

  const columns =
    _currentGranularity === "daily"
      ? [
          "date",
          "totalRecords",
          "totalBdaPages",
          "totalFileSizeBytes",
          "totalBedrockInputTokens",
          "totalBedrockOutputTokens",
        ]
      : [
          "tenantId",
          "totalRecords",
          "totalBdaPages",
          "totalFileSizeBytes",
          "totalBedrockInputTokens",
          "totalBedrockOutputTokens",
        ];

  const header = columns.map((col) => `"${col}"`).join(",");
  const rows = _currentData.map((row) =>
    columns
      .map((col) => {
        const val = row[col] ?? "";
        return `"${String(val).replace(/"/g, '""')}"`;
      })
      .join(","),
  );
  const csv = [header, ...rows].join("\n");

  const blob = new Blob([csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `usage-${_yearSelect.value}-${_monthSelect.value}-${_currentGranularity}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}
