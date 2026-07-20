import * as MetricsService from "../../services/metrics.js";
import * as TenantContext from "../../utils/tenant-context.js";
import * as Toast from "../../utils/toast.js";
import { tpl } from "../../utils/tpl.js";
import { h } from "../../utils/dom.js";
import html from "./metrics.html";

const tmpl = tpl(html);

let _root;
let _startInput, _endInput, _loadBtn;
let _cardsEl, _statusEl, _codesEl, _classificationEl, _emptyEl;
let _tenantUnsub = null;
let _loadId = 0;

export function mount(root) {
  _root = root;
  root.replaceChildren(tmpl());

  _startInput = root.querySelector("#metrics-start");
  _endInput = root.querySelector("#metrics-end");
  _loadBtn = root.querySelector("#metrics-load-btn");
  _cardsEl = root.querySelector("#metrics-cards");
  _statusEl = root.querySelector("#metrics-status");
  _codesEl = root.querySelector("#metrics-codes");
  _classificationEl = root.querySelector("#metrics-classification");
  _emptyEl = root.querySelector("#metrics-empty");

  // Default to last 7 days
  const end = new Date();
  const start = new Date();
  start.setDate(end.getDate() - 7);
  _startInput.value = _fmt(start);
  _endInput.value = _fmt(end);

  _loadBtn.addEventListener("click", load);
  _tenantUnsub = TenantContext.onChange(() => load());

  load();
}

export function unmount(_root) {
  if (_tenantUnsub) {
    _tenantUnsub();
    _tenantUnsub = null;
  }
  _root = null;
}

function _fmt(d) {
  return d.toISOString().slice(0, 10);
}

async function load() {
  const startDate = _startInput.value;
  const endDate = _endInput.value;
  if (!startDate) return;

  const thisLoad = ++_loadId;

  _cardsEl.replaceChildren();
  _statusEl.replaceChildren();
  _codesEl.replaceChildren();
  _classificationEl.replaceChildren();
  _emptyEl.textContent = "Loading...";
  _emptyEl.classList.remove("hidden");

  try {
    const resp = await MetricsService.get({
      startDate,
      endDate,
      tenantId: TenantContext.getTenantId(),
    });

    if (thisLoad !== _loadId) return;

    const summary = resp.summary;
    if (!summary || summary.totalRecords === 0) {
      _emptyEl.textContent = "No data available for this period.";
      return;
    }

    _emptyEl.classList.add("hidden");
    renderCards(summary);
    renderStatus(summary.byStatus);
    renderCodes(summary.byResponseCode);
    renderClassification(summary.byClassification);
  } catch (e) {
    if (thisLoad !== _loadId) return;
    _emptyEl.textContent = `Failed to load: ${e.message}`;
    Toast.show(`Metrics load failed: ${e.message}`);
  }
}

function renderCards(summary) {
  const timing = summary.timingStats || {};
  const totalRecords = summary.totalRecords || 0;
  const bdaInvocations = summary.totalBdaInvocations || 0;
  const failedCount = (summary.byStatus || {}).failed || 0;
  const errorRate = totalRecords > 0 ? ((failedCount / totalRecords) * 100).toFixed(1) : "0";

  const cards = [
    { label: "Documents", value: totalRecords.toLocaleString(), status: "neutral" },
    {
      label: "Extraction Avg",
      value: `${(timing.bdaProcessingTimeAvg || 0).toFixed(1)}s`,
      status: timing.bdaProcessingTimeAvg < 20 ? "good" : "warn",
    },
    {
      label: "Queue Time",
      value: `${(timing.bdaWaitTimeAvg || 0).toFixed(1)}s`,
      status: timing.bdaWaitTimeAvg < 5 ? "good" : "warn",
    },
    {
      label: "Error Rate",
      value: `${errorRate}%`,
      status: parseFloat(errorRate) <= 1 ? "good" : parseFloat(errorRate) <= 3 ? "warn" : "bad",
    },
    { label: "Extractions", value: bdaInvocations.toLocaleString(), status: "neutral" },
    {
      label: "End-to-End Avg",
      value: `${(timing.totalProcessingTimeAvg || 0).toFixed(1)}s`,
      status: timing.totalProcessingTimeAvg < 30 ? "good" : "warn",
    },
  ];

  _cardsEl.replaceChildren(
    ...cards.map((card) =>
      h(
        "div",
        { className: `metric-card metric-card--${card.status}` },
        h("div", { className: "metric-card-value" }, card.value),
        h("div", { className: "metric-card-label" }, card.label),
      ),
    ),
  );
}

function renderStatus(byStatus) {
  if (!byStatus || Object.keys(byStatus).length === 0) return;

  const sorted = Object.entries(byStatus)
    .map(([k, v]) => [_humanizeStatus(k), v])
    .sort((a, b) => b[1] - a[1]);
  const max = sorted[0][1];

  _statusEl.replaceChildren(
    h("h3", { className: "metrics-panel-title" }, "Status Breakdown"),
    ...sorted.map(([status, count]) =>
      h(
        "div",
        { className: "metrics-bar-row" },
        h("span", { className: "metrics-bar-label" }, status),
        h(
          "div",
          { className: "metrics-bar-track" },
          h("div", {
            className: `metrics-bar-fill metrics-bar-fill--${_statusColor(status)}`,
            style: `width: ${(count / max) * 100}%`,
          }),
        ),
        h("span", { className: "metrics-bar-value" }, count.toLocaleString()),
      ),
    ),
  );
}

export function computeBarData(entries, { filterNull = false, sortByKey = false } = {}) {
  let items = Object.entries(entries);
  if (filterNull) items = items.filter(([k]) => k !== "null");
  if (sortByKey) items.sort((a, b) => a[0].localeCompare(b[0]));
  else items.sort((a, b) => b[1] - a[1]);
  const max = items.length > 0 ? Math.max(...items.map(([, c]) => c)) : 1;
  return items.map(([label, count]) => ({
    label,
    count,
    widthPct: (count / max) * 100,
  }));
}

function renderCodes(byResponseCode) {
  if (!byResponseCode || Object.keys(byResponseCode).length === 0) return;

  const bars = computeBarData(byResponseCode, { filterNull: true, sortByKey: true });

  _codesEl.replaceChildren(
    h("h3", { className: "metrics-panel-title" }, "Response Codes"),
    ...bars.map(({ label, count, widthPct }) =>
      h(
        "div",
        { className: "metrics-bar-row" },
        h("span", { className: "metrics-bar-label" }, label),
        h(
          "div",
          { className: "metrics-bar-track" },
          h("div", {
            className: `metrics-bar-fill metrics-bar-fill--${_codeColor(label)}`,
            style: `width: ${widthPct}%`,
          }),
        ),
        h("span", { className: "metrics-bar-value" }, count.toLocaleString()),
      ),
    ),
  );
}

function renderClassification(byClassification) {
  if (!byClassification || Object.keys(byClassification).length === 0) return;

  const sorted = Object.entries(byClassification)
    .map(([k, v]) => [k === "null" ? "Unclassified" : k, v])
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10);
  const max = sorted[0][1];

  _classificationEl.replaceChildren(
    h("h3", { className: "metrics-panel-title" }, "Top Document Types"),
    ...sorted.map(([docType, count]) =>
      h(
        "div",
        { className: "metrics-bar-row" },
        h("span", { className: "metrics-bar-label" }, docType),
        h(
          "div",
          { className: "metrics-bar-track" },
          h("div", {
            className: "metrics-bar-fill metrics-bar-fill--primary",
            style: `width: ${(count / max) * 100}%`,
          }),
        ),
        h("span", { className: "metrics-bar-value" }, count.toLocaleString()),
      ),
    ),
  );
}

export function _statusColor(status) {
  if (status === "Success") return "success";
  if (status === "Failed") return "danger";
  return "neutral";
}

export function _humanizeStatus(status) {
  const map = {
    success: "Success",
    failed: "Failed",
    no_document_detected: "No Document Detected",
    no_custom_blueprint_matched: "No Blueprint Matched",
    blurry_document_detected: "Blurry Document",
    password_protected: "Password Protected",
    multiple_documents_single_page: "Multiple Documents",
    ai_consent_declined: "AI Consent Declined",
    conversion_failed: "Conversion Failed",
  };
  return map[status] || status.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function _codeColor(code) {
  if (code.startsWith("000")) return "success";
  if (code.startsWith("0")) return "warn";
  if (code.startsWith("1")) return "warn";
  return "danger";
}
