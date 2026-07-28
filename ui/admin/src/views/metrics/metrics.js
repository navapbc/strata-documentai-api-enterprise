import * as MetricsService from "../../services/metrics.js";
import * as TenantContext from "../../utils/tenant-context.js";
import * as Toast from "../../utils/toast.js";
import { tpl } from "../../utils/tpl.js";
import { h } from "../../utils/dom.js";
import html from "./metrics.html";

const tmpl = tpl(html);

let _root;
let _startInput, _endInput, _loadBtn, _timeframeSelect, _customRange;
let _cardsEl, _codesEl, _codesLabelEl, _classificationEl, _classificationLabelEl, _emptyEl;
let _tenantUnsub = null;
let _loadId = 0;

export function mount(root) {
  _root = root;
  root.replaceChildren(tmpl());

  _startInput = root.querySelector("#metrics-start");
  _endInput = root.querySelector("#metrics-end");
  _loadBtn = root.querySelector("#metrics-load-btn");
  _timeframeSelect = root.querySelector("#metrics-timeframe");
  _customRange = root.querySelector("#metrics-custom-range");
  _cardsEl = root.querySelector("#metrics-cards");
  _codesEl = root.querySelector("#metrics-codes");
  _codesLabelEl = root.querySelector("#metrics-codes-label");
  _classificationEl = root.querySelector("#metrics-classification");
  _classificationLabelEl = root.querySelector("#metrics-classification-label");
  _emptyEl = root.querySelector("#metrics-empty");

  _timeframeSelect.addEventListener("change", () => {
    if (_timeframeSelect.value === "custom") {
      _customRange.classList.remove("hidden");
    } else {
      _customRange.classList.add("hidden");
      load();
    }
  });

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

function _getDateRange() {
  const val = _timeframeSelect.value;
  if (val === "custom") {
    return { startDate: _startInput.value, endDate: _endInput.value };
  }
  const end = new Date();
  const start = new Date();
  start.setDate(end.getDate() - parseInt(val));
  return { startDate: _fmt(start), endDate: _fmt(end) };
}

async function load() {
  const { startDate, endDate } = _getDateRange();
  if (!startDate) return;

  const thisLoad = ++_loadId;

  _cardsEl.replaceChildren();
  _codesEl.replaceChildren();
  _codesLabelEl.replaceChildren();
  _classificationEl.replaceChildren();
  _classificationLabelEl.replaceChildren();
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
    renderCodes(summary.byResponseCode);
    renderClassification(summary.byClassification);
  } catch (e) {
    if (thisLoad !== _loadId) return;
    _emptyEl.textContent = `Failed to load: ${e.message}`;
    Toast.show(`Metrics load failed: ${e.message}`, "error");
  }
}

const ICONS = {
  documents: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"/></svg>`,
  extractions: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"/></svg>`,
  check: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>`,
  error: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v4m0 4h.01M10.29 3.86 1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/></svg>`,
  blurry: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/><circle cx="12" cy="12" r="3" stroke-dasharray="2 2"/></svg>`,
  nodoc: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"/><line x1="9" y1="9" x2="15" y2="15"/><line x1="15" y1="9" x2="9" y2="15"/></svg>`,
  lock: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path stroke-linecap="round" stroke-linejoin="round" d="M7 11V7a5 5 0 0110 0v4"/></svg>`,
  stack: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>`,
  timer: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path stroke-linecap="round" stroke-linejoin="round" d="M12 7v5l3 3"/></svg>`,
  queue: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 2h12v6l-4 4 4 4v6H6v-6l4-4-4-4V2z"/></svg>`,
  endtoend: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M5 12h14M15 7l5 5-5 5"/></svg>`,
};

function svgEl(svgStr) {
  const div = document.createElement("div");
  div.innerHTML = svgStr;
  return div.firstElementChild;
}

function renderCards(summary) {
  const timing = summary.timingStats || {};
  const totalRecords = summary.totalRecords || 0;
  const bdaInvocations = summary.totalBdaInvocations || 0;
  const byCode = summary.byResponseCode || {};
  const successCount = Object.entries(byCode).find(([k]) => k.startsWith("000"))?.[1] || 0;
  const failedCount = (summary.byStatus || {}).failed || 0;
  const blurryCount = (summary.byStatus || {}).blurry_document_detected || 0;
  const noDocCount = (summary.byStatus || {}).no_document_detected || 0;
  const passwordCount = (summary.byStatus || {}).password_protected || 0;
  const multipleDocsCount = (summary.byStatus || {}).multiple_documents_single_page || 0;

  const volumeCards = [
    { label: "Document Count", value: totalRecords.toLocaleString(), status: "neutral", icon: ICONS.documents },
    { label: "Number of Extractions", value: bdaInvocations.toLocaleString(), status: "neutral", icon: ICONS.extractions },
    { label: "Validation Passed", value: successCount.toLocaleString(), status: "good", icon: ICONS.check },
  ];

  const failureCards = [
    { label: "Failed", value: failedCount.toLocaleString(), status: failedCount > 0 ? "bad" : "good", icon: ICONS.error },
    { label: "Blurry", value: blurryCount.toLocaleString(), status: blurryCount > 0 ? "bad" : "good", icon: ICONS.blurry },
    { label: "No Document Detected", value: noDocCount.toLocaleString(), status: noDocCount > 0 ? "bad" : "good", icon: ICONS.nodoc },
    { label: "Multiple Documents on Page", value: multipleDocsCount.toLocaleString(), status: multipleDocsCount > 0 ? "bad" : "good", icon: ICONS.stack },
    { label: "Password Protected", value: passwordCount.toLocaleString(), status: passwordCount > 0 ? "warn" : "good", icon: ICONS.lock },
  ];

  const timingCards = [
    {
      label: "Extraction Time Avg.",
      value: `${(timing.bdaProcessingTimeAvg || 0).toFixed(1)}s`,
      status: timing.bdaProcessingTimeAvg < 20 ? "good" : "warn",
      icon: ICONS.timer,
    },
    {
      label: "Queue Time Avg.",
      value: `${(timing.bdaWaitTimeAvg || 0).toFixed(1)}s`,
      status: timing.bdaWaitTimeAvg < 5 ? "good" : "warn",
      icon: ICONS.queue,
    },
    {
      label: "End-to-End Avg",
      value: `${(timing.totalProcessingTimeAvg || 0).toFixed(1)}s`,
      status: timing.totalProcessingTimeAvg < 30 ? "good" : "warn",
      icon: ICONS.endtoend,
    },
  ];

  function renderCardEl(card) {
    return h(
      "div",
      { className: `metric-card metric-card--${card.status}` },
      h("div", { className: "metric-card-header" },
        h("div", { className: "metric-card-label" }, card.label),
        h("div", { className: "metric-card-icon" }, svgEl(card.icon)),
      ),
      h("div", { className: "metric-card-value" }, card.value),
    );
  }

  _cardsEl.replaceChildren(
    h("div", { className: "metrics-card-group-label" }, "Volume"),
    h("div", { className: "metrics-cards-row" }, ...volumeCards.map(renderCardEl)),
    h("div", { className: "metrics-cards-row" }, ...failureCards.map(renderCardEl)),
    h("div", { className: "metrics-cards-row" }, ...timingCards.map(renderCardEl)),
  );
}

function renderClassification(byClassification) {
  if (!byClassification || Object.keys(byClassification).length === 0) return;

  const sorted = Object.entries(byClassification)
    .map(([k, v]) => [k === "null" ? "Unclassified" : k, v])
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10);
  const max = sorted[0][1];

  _classificationLabelEl.replaceChildren(
    h("div", { className: "metrics-card-group-label" }, "Top Document Types"),
  );
  _classificationEl.replaceChildren(
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

function renderCodes(byResponseCode) {
  if (!byResponseCode || Object.keys(byResponseCode).length === 0) return;

  const bars = computeBarData(byResponseCode, { filterNull: true, sortByKey: true });

  _codesLabelEl.replaceChildren(
    h("div", { className: "metrics-card-group-label" }, "Response Codes"),
  );
  _codesEl.replaceChildren(
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
