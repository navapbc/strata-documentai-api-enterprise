import * as MetricsService from "../../services/metrics.js";
import * as TenantContext from "../../utils/tenant-context.js";
import * as Toast from "../../utils/toast.js";
import { tpl } from "../../utils/tpl.js";
import { h } from "../../utils/dom.js";
import html from "./metrics.html";

const tmpl = tpl(html);

let _root;
let _startInput, _endInput, _loadBtn, _timeframeSelect, _customRange;
let _tabVolume, _tabDocTypes, _tabCodes, _tabTiming;
let _emptyEl;
let _tenantUnsub = null;
let _loadId = 0;
let _activeTab = "volume";

export function mount(root) {
  _root = root;
  root.replaceChildren(tmpl());

  _startInput = root.querySelector("#metrics-start");
  _endInput = root.querySelector("#metrics-end");
  _loadBtn = root.querySelector("#metrics-load-btn");
  _timeframeSelect = root.querySelector("#metrics-timeframe");
  _customRange = root.querySelector("#metrics-custom-range");
  _tabVolume = root.querySelector("#metrics-tab-volume");
  _tabDocTypes = root.querySelector("#metrics-tab-document-types");
  _tabCodes = root.querySelector("#metrics-tab-response-codes");
  _tabTiming = root.querySelector("#metrics-tab-timing");
  _emptyEl = root.querySelector("#metrics-empty");

  _timeframeSelect.addEventListener("change", () => {
    if (_timeframeSelect.value === "custom") {
      _customRange.classList.remove("hidden");
    } else {
      _customRange.classList.add("hidden");
      load();
    }
  });

  root.querySelectorAll(".metrics-tab").forEach((btn) => {
    btn.addEventListener("click", () => {
      _activeTab = btn.dataset.tab;
      root.querySelectorAll(".metrics-tab").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      root.querySelectorAll(".metrics-tab-panel").forEach((p) => p.classList.add("hidden"));
      root.querySelector(`#metrics-tab-${_activeTab}`).classList.remove("hidden");
    });
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

  _tabVolume.replaceChildren();
  _tabDocTypes.replaceChildren();
  _tabCodes.replaceChildren();
  _tabTiming.replaceChildren();
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
    renderVolume(summary, summary.timingStats);
    renderDocumentTypes(summary.byClassification);
    renderResponseCodes(summary.byResponseCode);
    renderTiming(summary.timingStats);
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
  error: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path stroke-linecap="round" stroke-linejoin="round" d="M15 9l-6 6M9 9l6 6"/></svg>`,
  blurry: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23" stroke-linecap="round"/></svg>`,
  nodoc: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"/><line x1="9" y1="9" x2="15" y2="15"/><line x1="15" y1="9" x2="9" y2="15"/></svg>`,
  lock: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path stroke-linecap="round" stroke-linejoin="round" d="M7 11V7a5 5 0 0110 0v4"/></svg>`,
  stack: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>`,
  timer: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path stroke-linecap="round" stroke-linejoin="round" d="M12 7v5l3 3"/></svg>`,
  queue: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 2h12v6l-4 4 4 4v6H6v-6l4-4-4-4V2z"/></svg>`,
  hand: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M10 15v4a3 3 0 003 3l4-9V2H5.72a2 2 0 00-2 1.7l-1.38 9a2 2 0 002 2.3H10z"/><path stroke-linecap="round" stroke-linejoin="round" d="M17 2h2.67A2.31 2.31 0 0122 4v7a2.31 2.31 0 01-2.33 2H17"/></svg>`,
  skip: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="4.93" y1="4.93" x2="19.07" y2="19.07"/></svg>`,
  missingfields: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/><line x1="9" y1="13" x2="13" y2="13"/><line x1="9" y1="17" x2="11" y2="17"/></svg>`,
  lowconf: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 5v14M5 12l7 7 7-7"/></svg>`,
  miscat: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M20.59 13.41l-7.17 7.17a2 2 0 01-2.83 0L2 12V2h10l8.59 8.59a2 2 0 010 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></svg>`,
  funnelArrow: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M5 12h14M15 7l5 5-5 5"/></svg>`,
  endtoend: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 21V4m0 0h12l-3 4 3 4H4"/></svg>`,
};

function svgEl(svgStr) {
  const div = document.createElement("div");
  // eslint-disable-next-line no-unsanitized/property -- svgStr is always a hardcoded trusted constant from the ICONS object
  div.innerHTML = svgStr;
  return div.firstElementChild;
}

function renderCardEl(card) {
  return h(
    "div",
    { className: `metric-card metric-card--${card.status}` },
    h(
      "div",
      { className: "metric-card-header" },
      h("div", { className: "metric-card-label" }, card.label),
      h("div", { className: "metric-card-icon" }, svgEl(card.icon)),
    ),
    h("div", { className: "metric-card-value" }, card.value),
  );
}

function _codeCount(byCode, prefix) {
  return Object.entries(byCode)
    .filter(([k]) => k.startsWith(prefix))
    .reduce((sum, [, v]) => sum + v, 0);
}

function renderVolume(summary, timing = {}) {
  const totalRecords = summary.totalRecords || 0;
  const bdaInvocations = summary.totalExtractionInvocations ?? summary.totalBdaInvocations ?? 0;
  const byCode = summary.byResponseCode || {};
  const successCount = _codeCount(byCode, "000");
  const blueprintMatched =
    summary.totalDocumentsRecognized ??
    _codeCount(byCode, "101") +
      _codeCount(byCode, "102") +
      _codeCount(byCode, "105") +
      successCount;

  const extractionPct =
    totalRecords > 0 ? ((bdaInvocations / totalRecords) * 100).toFixed(1) : null;
  const blueprintPct =
    bdaInvocations > 0 ? ((blueprintMatched / bdaInvocations) * 100).toFixed(1) : null;
  const validationPct =
    blueprintMatched > 0 ? ((successCount / blueprintMatched) * 100).toFixed(1) : null;

  const funnelStages = [
    { label: "Documents Received", value: totalRecords, pct: null, bg: "#dbeafe" },
    { label: "Extractions", value: bdaInvocations, pct: extractionPct, bg: "#bfdbfe" },
    {
      label: "Document Type Identified",
      value: blueprintMatched,
      pct: blueprintPct,
      bg: "#e0e7ff",
    },
    { label: "Validation Passed", value: successCount, pct: validationPct, bg: "#d1fae5" },
  ];

  const maxVal = funnelStages[0].value || 1;
  const funnelEl = h(
    "div",
    { className: "metrics-funnel" },
    ...funnelStages.map((stage, i) => {
      const heightPct = (stage.value / maxVal) * 100;
      const topInset = (100 - heightPct) / 2;
      const next = funnelStages[i + 1];
      const nextHeightPct = next ? (next.value / maxVal) * 100 : heightPct;
      const nextTopInset = (100 - nextHeightPct) / 2;
      const clip = `polygon(0% ${topInset}%, 100% ${nextTopInset}%, 100% ${100 - nextTopInset}%, 0% ${100 - topInset}%)`;
      return h(
        "div",
        { className: "metrics-funnel-stage", style: `background:${stage.bg};clip-path:${clip}` },
        h("div", { className: "metrics-funnel-value" }, stage.value.toLocaleString()),
        h("div", { className: "metrics-funnel-label" }, stage.label),
        stage.pct !== null
          ? h("div", { className: "metrics-funnel-pct" }, `${stage.pct}%`)
          : h("div", { className: "metrics-funnel-pct" }, ""),
      );
    }),
  );

  // Extraction failures: didn't reach BDA (103, 104, 106, 400, 999, 004, 003)
  const extractionGap = totalRecords - bdaInvocations;
  const extractionFailures = [
    { label: "No Document Detected", value: _codeCount(byCode, "103"), icon: ICONS.nodoc },
    { label: "Blurry Document", value: _codeCount(byCode, "104"), icon: ICONS.blurry },
    { label: "Password Protected", value: _codeCount(byCode, "106"), icon: ICONS.lock },
    { label: "Multiple Docs on Page", value: _codeCount(byCode, "400"), icon: ICONS.stack },
    { label: "System Error", value: _codeCount(byCode, "999"), icon: ICONS.error },
    {
      label: "Not Chosen for Extraction",
      value: _codeCount(byCode, "004"),
      icon: ICONS.skip,
      warn: true,
    },
    {
      label: "AI Consent Declined",
      value: _codeCount(byCode, "003"),
      icon: ICONS.hand,
      warn: true,
    },
  ];
  const extractionAccounted = extractionFailures.reduce((s, c) => s + c.value, 0);
  if (extractionGap - extractionAccounted > 0)
    extractionFailures.push({
      label: "Other",
      value: extractionGap - extractionAccounted,
      icon: ICONS.error,
    });

  const validationGap = blueprintMatched - successCount;
  const validationFailures = [
    { label: "Missing Fields", value: _codeCount(byCode, "101"), icon: ICONS.missingfields },
    { label: "Miscategorized", value: _codeCount(byCode, "102"), icon: ICONS.miscat },
    { label: "Low Confidence", value: _codeCount(byCode, "105"), icon: ICONS.lowconf },
  ];
  const validationAccounted = validationFailures.reduce((s, c) => s + c.value, 0);
  if (validationGap - validationAccounted > 0)
    validationFailures.push({
      label: "Other",
      value: validationGap - validationAccounted,
      icon: ICONS.error,
    });

  function failureGroup(label, cards) {
    return h(
      "div",
      { className: "metrics-failure-group" },
      h("div", { className: "metrics-failure-group-label" }, label),
      h(
        "div",
        { className: "metrics-cards-row" },
        ...cards.map((c) =>
          renderCardEl({
            ...c,
            value: c.value.toLocaleString(),
            status: c.value === 0 ? "good" : c.warn ? "warn" : "bad",
          }),
        ),
      ),
    );
  }

  const avg = (timing.totalProcessingTimeAvg || 0).toFixed(1);
  const timingLink = h(
    "button",
    { className: "metrics-timing-callout-link" },
    "see Timing tab for breakdown",
  );
  timingLink.addEventListener("click", () =>
    _root.querySelector(".metrics-tab[data-tab='timing']").click(),
  );
  const timingCallout = h(
    "div",
    { className: "metrics-timing-callout" },
    h("span", {}, `End-to-end avg ${avg}s - `),
    timingLink,
  );

  _tabVolume.replaceChildren(
    funnelEl,
    failureGroup(
      `${extractionGap.toLocaleString()} documents did not qualify for extraction`,
      extractionFailures,
    ),
    failureGroup(
      `${validationGap.toLocaleString()} extracted documents did not satisfy business rules`,
      validationFailures,
    ),
    timingCallout,
  );
}

function renderDocumentTypes(byClassification) {
  if (!byClassification || Object.keys(byClassification).length === 0) return;

  const sorted = Object.entries(byClassification)
    .map(([k, v]) => [k === "null" ? "Unclassified" : k, v])
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10);
  const max = sorted[0][1];

  _tabDocTypes.replaceChildren(
    h(
      "div",
      { className: "metrics-panel" },
      ...sorted.map(([docType, count]) =>
        h(
          "div",
          { className: "metrics-bar-row" },
          h("span", { className: "metrics-bar-label", title: docType }, docType),
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
    ),
  );
}

function renderResponseCodes(byResponseCode) {
  if (!byResponseCode || Object.keys(byResponseCode).length === 0) return;

  const bars = computeBarData(byResponseCode, { filterNull: true, sortByKey: true });

  _tabCodes.replaceChildren(
    h(
      "div",
      { className: "metrics-panel" },
      ...bars.map(({ label, count, widthPct }) =>
        h(
          "div",
          { className: "metrics-bar-row" },
          h("span", { className: "metrics-bar-label", title: label }, label),
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
    ),
  );
}

function renderTiming(timing = {}) {
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

  _tabTiming.replaceChildren(
    h("div", { className: "metrics-cards-row" }, ...timingCards.map(renderCardEl)),
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
