import * as UsageService from "../../services/usage.js";
import * as Toast from "../../utils/toast.js";
import { tpl } from "../../utils/tpl.js";
import { h } from "../../utils/dom.js";
import html from "./usage.html";

const tmpl = tpl(html);

let _root;
let _monthInput, _granularitySelect, _downloadBtn, _tableContainer, _empty;
let _currentData = [];
let _currentGranularity = "monthly";

export function mount(root) {
  _root = root;
  root.replaceChildren(tmpl());

  _monthInput = root.querySelector("#usage-month");
  _granularitySelect = root.querySelector("#usage-granularity");
  _downloadBtn = root.querySelector("#usage-download-btn");
  _tableContainer = root.querySelector("#usage-table-container");
  _empty = root.querySelector("#usage-empty");

  // Default to current month
  const now = new Date();
  _monthInput.value = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;

  _monthInput.addEventListener("change", load);
  _granularitySelect.addEventListener("change", load);
  _downloadBtn.addEventListener("click", downloadCsv);

  load();
}

export function unmount(_root) {
  _root = null;
  _currentData = [];
}

async function load() {
  const month = _monthInput.value;
  _currentGranularity = _granularitySelect.value;

  _empty.textContent = "Loading...";
  _empty.classList.remove("hidden");
  _tableContainer.querySelectorAll("table").forEach((t) => t.remove());

  try {
    const resp = await UsageService.get({ month, granularity: _currentGranularity });

    if (_currentGranularity === "daily") {
      _currentData = resp.days || [];
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
          { key: "total_records", label: "Documents" },
          { key: "total_bda_invocations", label: "BDA Invocations" },
          { key: "total_pages", label: "Pages Detected" },
          { key: "total_bda_pages", label: "BDA Pages" },
          { key: "total_file_size_bytes", label: "File Size (bytes)" },
          { key: "total_bedrock_input_tokens", label: "Input Tokens" },
          { key: "total_bedrock_output_tokens", label: "Output Tokens" },
        ]
      : [
          { key: "tenant_id", label: "Tenant" },
          { key: "total_records", label: "Documents" },
          { key: "total_bda_invocations", label: "BDA Invocations" },
          { key: "total_bda_pages", label: "BDA Pages" },
          { key: "total_file_size_bytes", label: "File Size (bytes)" },
          { key: "total_bedrock_input_tokens", label: "Input Tokens" },
          { key: "total_bedrock_output_tokens", label: "Output Tokens" },
        ];

  const thead = h(
    "thead",
    {},
    h("tr", {}, ...columns.map((col) => h("th", {}, col.label))),
  );

  const tbody = h(
    "tbody",
    {},
    ..._currentData.map((row) =>
      h(
        "tr",
        {},
        ...columns.map((col) => h("td", {}, formatCell(col.key, row[col.key]))),
      ),
    ),
  );

  const table = h("table", { className: "detail-table usage-table" }, thead, tbody);
  _tableContainer.appendChild(table);
}

function formatCell(key, value) {
  if (value == null) return "-";
  if (key === "total_file_size_bytes") {
    return `${(value / 1024 / 1024).toFixed(1)} MB`;
  }
  if (typeof value === "number") {
    return value.toLocaleString();
  }
  return String(value);
}

function downloadCsv() {
  if (!_currentData.length) return;

  const columns =
    _currentGranularity === "daily"
      ? ["date", "total_records", "total_bda_invocations", "total_pages", "total_bda_pages", "total_file_size_bytes", "total_bedrock_input_tokens", "total_bedrock_output_tokens"]
      : ["tenant_id", "total_records", "total_bda_invocations", "total_bda_pages", "total_file_size_bytes", "total_bedrock_input_tokens", "total_bedrock_output_tokens"];

  const header = columns.join(",");
  const rows = _currentData.map((row) =>
    columns.map((col) => row[col] ?? "").join(","),
  );
  const csv = [header, ...rows].join("\n");

  const blob = new Blob([csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `usage-${_monthInput.value}-${_currentGranularity}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}
