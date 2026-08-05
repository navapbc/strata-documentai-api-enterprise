import {
  Chart,
  BarController,
  LineController,
  BarElement,
  LineElement,
  PointElement,
  CategoryScale,
  LinearScale,
  Tooltip,
  Legend,
  Filler,
} from "chart.js";
import * as MetricsService from "../../services/metrics.js";
import * as TenantContext from "../../utils/tenant-context.js";
import * as Toast from "../../utils/toast.js";
import { tpl } from "../../utils/tpl.js";
import { h } from "../../utils/dom.js";
import html from "./metrics.html";

Chart.register(
  BarController,
  LineController,
  BarElement,
  LineElement,
  PointElement,
  CategoryScale,
  LinearScale,
  Tooltip,
  Legend,
  Filler,
);

const tmpl = tpl(html);

let _root;
let _startInput, _endInput, _loadBtn, _timeframeSelect, _customRange;
let _tabVolume, _tabDocTypes, _tabOutcomes, _tabTiming;
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
  _tabOutcomes = root.querySelector("#metrics-tab-outcomes");
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

  const validTabs = ["volume", "document-types", "outcomes", "timing"];
  const hashTab = location.hash.replace("#", "").split("/")[1];
  _activeTab = validTabs.includes(hashTab) ? hashTab : "volume";
  root.querySelectorAll(".metrics-tab").forEach((btn) => {
    if (btn.dataset.tab === _activeTab) btn.classList.add("active");
    else btn.classList.remove("active");
  });
  root.querySelectorAll(".metrics-tab-panel").forEach((p) => p.classList.add("hidden"));
  root.querySelector(`#metrics-tab-${_activeTab}`)?.classList.remove("hidden");

  root.querySelectorAll(".metrics-tab").forEach((btn) => {
    btn.addEventListener("click", () => {
      _activeTab = btn.dataset.tab;
      location.hash = `metrics/${_activeTab}`;
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
  if (val === "1") {
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);
    const d = _fmt(yesterday);
    return { startDate: d, endDate: d };
  }
  const end = new Date();
  const start = new Date();
  start.setDate(end.getDate() - parseInt(val));
  return { startDate: _fmt(start), endDate: _fmt(end) };
}

async function load() {
  const { startDate, endDate } = _getDateRange();
  if (!startDate) return;
  if (endDate && startDate > endDate) {
    Toast.show("End date must be after start date.", "error");
    return;
  }
  if (startDate && endDate) {
    const days = (new Date(endDate) - new Date(startDate)) / 86400000;
    if (days > 90) {
      Toast.show("Custom range cannot exceed 90 days.", "error");
      return;
    }
  }
  const thisLoad = ++_loadId;

  _tabVolume.replaceChildren();
  _tabDocTypes.replaceChildren();
  _tabOutcomes.replaceChildren();
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
    const dailyStats = resp.dailyStats || [];
    renderVolume(summary, dailyStats);
    renderDocumentTypes(summary.byClassification);
    renderOutcomes(summary, summary.byResponseCode);
    renderTiming(summary.timingStats, dailyStats);
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
  other: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"><rect x="25.5" y="5.5" width="17" height="17"/><rect x="25.5" y="25.5" width="17" height="17"/><rect x="5.5" y="5.5" width="17" height="17"/><rect x="5.5" y="25.5" width="17" height="17"/></svg>`,
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

function renderVolume(summary, dailyStats = []) {
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
    { label: "Documents Received", value: totalRecords, pct: null, bg: "#bfdbfe" },
    { label: "Extractions", value: bdaInvocations, pct: extractionPct, bg: "#93c5fd" },
    { label: "Doc Type Identified", value: blueprintMatched, pct: blueprintPct, bg: "#a5b4fc" },
    { label: "Validation Passed", value: successCount, pct: validationPct, bg: "#86efac" },
  ];

  const funnelCanvas = document.createElement("canvas");
  const funnelWrap = h("div", { className: "metrics-chart metrics-funnel-chart" }, funnelCanvas);
  new Chart(funnelCanvas, {
    type: "bar",
    data: {
      labels: funnelStages.map((s) => s.label),
      datasets: [
        {
          data: funnelStages.map((s) => s.value),
          backgroundColor: funnelStages.map((s) => s.bg),
          borderRadius: 4,
          borderSkipped: false,
          barPercentage: 0.975,
          categoryPercentage: 0.975,
        },
      ],
    },
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      events: [],
      plugins: { legend: { display: false }, tooltip: { enabled: false } },
      scales: {
        x: { display: false, beginAtZero: true, max: totalRecords || 1 },
        y: { display: false },
      },
    },
    plugins: [
      {
        afterDraw(chart) {
          const {
            ctx,
            scales: { y },
          } = chart;
          ctx.save();
          funnelStages.forEach((stage, i) => {
            const yPos = y.getPixelForValue(i);
            ctx.textBaseline = "middle";
            ctx.textAlign = "left";
            ctx.fillStyle = "#111827";
            ctx.font = "bold 13px sans-serif";
            ctx.fillText(stage.value.toLocaleString(), 10, yPos - 14);
            ctx.fillStyle = "#374151";
            ctx.font = "600 11px sans-serif";
            ctx.fillText(stage.label, 10, yPos);
            if (stage.pct) {
              ctx.fillStyle = "#6b7280";
              ctx.font = "11px sans-serif";
              ctx.fillText(`${stage.pct}%`, 10, yPos + 14);
            }
          });
          ctx.restore();
        },
      },
    ],
  });

  // Row 1: Funnel + Documents per Day + Heatmap
  const funnelWrapCol = h(
    "div",
    { className: "metrics-split-third" },
    h("div", { className: "metrics-chart-label" }, "Document processing pipeline"),
    funnelWrap,
  );

  const docsPerDayWrap = h("div", { className: "metrics-split-third" });
  if (dailyStats.length >= 1) {
    docsPerDayWrap.appendChild(
      h("div", { className: "metrics-chart-label" }, "Documents Received per Day (UTC)"),
    );
    const chartWrap = h("div", { className: "metrics-chart" });
    const canvas = document.createElement("canvas");
    chartWrap.appendChild(canvas);
    new Chart(canvas, buildVolumeChartConfig(dailyStats));
    docsPerDayWrap.appendChild(chartWrap);
  }

  const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
  const hourWrap = h(
    "div",
    { className: "metrics-split-third" },
    h("div", { className: "metrics-chart-label" }, `Submissions by Hour of Day (${tz})`),
    buildHourHeatmapEl(dailyStats),
  );

  _tabVolume.replaceChildren(
    h("div", { className: "metrics-split-row" }, funnelWrapCol, docsPerDayWrap, hourWrap),
  );

  // Row 2: File Types + User Categories + Upload Methods
  const byFileType = summary.byFileType || {};
  const byUserCategory = summary.byUserCategory || {};
  const byUploadMethod = summary.byUploadMethod || {};

  function buildBarPanel(data, label) {
    const wrap = h("div", { className: "metrics-split-third" });
    const bars = computeBarData(data, { filterNull: true });
    wrap.appendChild(h("div", { className: "metrics-chart-label" }, label));
    if (bars.length > 0) {
      const total = bars.reduce((s, { count }) => s + count, 0);
      wrap.appendChild(
        h(
          "div",
          { className: "metrics-panel" },
          ...bars.map(({ label: l, count, widthPct }) =>
            h(
              "div",
              { className: "metrics-bar-row" },
              h("span", { className: "metrics-bar-label", title: l }, l),
              h(
                "div",
                { className: "metrics-bar-track" },
                h("div", {
                  className: "metrics-bar-fill metrics-bar-fill--primary",
                  style: `width: ${widthPct}%`,
                }),
              ),
              h("span", { className: "metrics-bar-value" }, count.toLocaleString()),
            ),
          ),
          h("div", { className: "metrics-bar-total" }, `Total: ${total.toLocaleString()}`),
        ),
      );
    } else {
      wrap.appendChild(h("div", { className: "metrics-empty-hint" }, "No data"));
    }
    return wrap;
  }

  _tabVolume.appendChild(
    h(
      "div",
      { className: "metrics-split-row" },
      buildBarPanel(byFileType, "File Types"),
      buildBarPanel(byUserCategory, "Tenant-Provided Document Categories"),
      buildBarPanel(byUploadMethod, "Upload Methods"),
    ),
  );
}

function renderOutcomes(summary, byResponseCode) {
  const byCode = summary.byResponseCode || {};
  const totalRecords = summary.totalRecords || 0;
  const bdaInvocations = summary.totalExtractionInvocations ?? summary.totalBdaInvocations ?? 0;
  const successCount = _codeCount(byCode, "0");
  const preExtractionStop = Math.max(0, totalRecords - bdaInvocations);
  const validationGap =
    _codeCount(byCode, "101") + _codeCount(byCode, "102") + _codeCount(byCode, "105");

  if (!byResponseCode || Object.keys(byResponseCode).length === 0) return;

  const bars = computeBarData(byResponseCode, { filterNull: true, sortByKey: true });

  const summaryCards = [
    {
      label: "Successful Responses",
      value: successCount.toLocaleString(),
      status: successCount > 0 ? "good" : "neutral",
      icon: ICONS.check,
    },
    {
      label: "Did Not Pass Rules",
      value: validationGap.toLocaleString(),
      status: validationGap > 0 ? "bad" : "good",
      icon: ICONS.missingfields,
    },
    {
      label: "Extraction Not Attempted",
      value: preExtractionStop.toLocaleString(),
      status: preExtractionStop > 0 ? "bad" : "good",
      icon: ICONS.nodoc,
    },
    {
      label: "Multiple Documents Detected",
      value: (_codeCount(byCode, "400") + _codeCount(byCode, "401")).toLocaleString(),
      status: _codeCount(byCode, "400") + _codeCount(byCode, "401") > 0 ? "bad" : "good",
      icon: ICONS.stack,
    },
  ];

  _tabOutcomes.replaceChildren(
    h("div", { className: "metrics-chart-label" }, "Outcome summary"),
    h("div", { className: "metrics-cards-row" }, ...summaryCards.map(renderCardEl)),
    h("div", { className: "metrics-chart-label" }, "Response Codes"),
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

function renderDocumentTypes(byClassification) {
  if (!byClassification || Object.keys(byClassification).length === 0) return;

  const sorted = Object.entries(byClassification)
    .map(([k, v]) => [k === "null" ? "Unclassified" : k, v])
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10);
  const max = sorted[0][1];

  _tabDocTypes.replaceChildren(
    h("div", { className: "metrics-chart-label" }, "Top Document Types"),
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

function renderTiming(timing = {}, dailyStats = []) {
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
    h("div", { className: "metrics-chart-label" }, "Timing metrics"),
    h("div", { className: "metrics-cards-row" }, ...timingCards.map(renderCardEl)),
  );

  if (dailyStats.length >= 1) {
    const timingWrap = h("div", { className: "metrics-split-half" });
    timingWrap.appendChild(
      h("div", { className: "metrics-chart-label" }, "Processing Time per Day (UTC)"),
    );
    const timingChartWrap = h("div", { className: "metrics-chart" });
    const timingCanvas = document.createElement("canvas");
    timingChartWrap.appendChild(timingCanvas);
    timingWrap.appendChild(timingChartWrap);
    new Chart(timingCanvas, buildTimingChartConfig(dailyStats));

    const dowWrap = h("div", { className: "metrics-split-half" });
    dowWrap.appendChild(
      h("div", { className: "metrics-chart-label" }, "Avg Processing Time by Day of Week"),
    );
    dowWrap.appendChild(buildDowTimingGridEl(dailyStats));

    _tabTiming.appendChild(h("div", { className: "metrics-split-row" }, timingWrap, dowWrap));
  }
}

function _labelDate(dateStr) {
  const [, m, d] = dateStr.split("-");
  return `${parseInt(m)}/${parseInt(d)}`;
}

export function buildVolumeChartConfig(dailyStats) {
  return {
    type: "bar",
    data: {
      labels: dailyStats.map((d) => _labelDate(d.date)),
      datasets: [
        {
          label: "Documents",
          data: dailyStats.map((d) => d.totalRecords ?? 0),
          backgroundColor: "#3b82f6",
          borderRadius: 3,
          borderSkipped: false,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      events: [],
      plugins: { legend: { display: false }, tooltip: { enabled: false } },
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: "#9ca3af", font: { size: 10 }, maxTicksLimit: 10 },
        },
        y: {
          grid: { display: false },
          ticks: { color: "#9ca3af", font: { size: 10 } },
          beginAtZero: true,
        },
      },
    },
    plugins: [
      {
        afterDraw(chart) {
          const {
            ctx,
            data,
            scales: { x, y },
          } = chart;
          ctx.save();
          ctx.font = "10px sans-serif";
          ctx.fillStyle = "#6b7280";
          ctx.textAlign = "center";
          data.datasets[0].data.forEach((val, i) => {
            if (!val) return;
            const xPos = x.getPixelForValue(i);
            const yPos = y.getPixelForValue(val) - 4;
            ctx.fillText(val.toLocaleString(), xPos, yPos);
          });
          ctx.restore();
        },
      },
    ],
  };
}

export function buildHourHeatmapEl(dailyStats) {
  const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
  const DAY_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  // grid[dow][hour] = count
  const grid = Array.from({ length: 7 }, () => Array(24).fill(0));

  for (const d of dailyStats) {
    if (!d.byHour || !d.date) continue;
    const dow = new Date(d.date + "T00:00:00").getDay();
    for (let utcHr = 0; utcHr < 24; utcHr++) {
      const count = d.byHour[String(utcHr)] ?? 0;
      if (!count) continue;
      const localHr = _utcHourToLocal(utcHr, d.date, tz);
      grid[dow][localHr] += count;
    }
  }

  const max = Math.max(...grid.flat());

  function intensity(count) {
    if (!count || max === 0) return 0;
    return Math.ceil((count / max) * 4);
  }

  const hourLabels = h(
    "div",
    { className: "metrics-hour-header" },
    h("div", { className: "metrics-hour-day-label" }), // spacer
    ...Array.from({ length: 24 }, (_, i) => {
      let label = "";
      if (i % 3 === 0) {
        const h12 = i % 12 || 12;
        label = `${h12}${i < 12 ? "a" : "p"}`;
      }
      return h("div", { className: "metrics-hour-label" }, label);
    }),
  );

  const rows = DAY_LABELS.map((day, dow) =>
    h(
      "div",
      { className: "metrics-hour-row" },
      h("div", { className: "metrics-hour-day-label" }, day),
      ...Array.from({ length: 24 }, (_, hr) => {
        const count = grid[dow][hr];
        const cell = h("div", {
          className: `metrics-heatmap-cell metrics-heatmap-cell--${intensity(count)}`,
        });
        const h12 = hr % 12 || 12;
        const ampm = hr < 12 ? "am" : "pm";
        cell.title = `${DAY_LABELS[dow]} ${h12}:00${ampm} (${tz}) - ${count.toLocaleString()} doc${count !== 1 ? "s" : ""}`;
        return cell;
      }),
    ),
  );

  const total = grid.flat().reduce((s, c) => s + c, 0);

  let peakLabel = "-",
    peakDow = 0,
    peakHr = 0;
  if (total > 0) {
    grid.forEach((hours, dow) =>
      hours.forEach((c, hr) => {
        if (c > grid[peakDow][peakHr]) {
          peakDow = dow;
          peakHr = hr;
        }
      }),
    );
    const h12 = peakHr % 12 || 12;
    const ampm = peakHr < 12 ? "am" : "pm";
    peakLabel = `${DAY_LABELS[peakDow]} ${h12}${ampm}`;
  }

  const footer = h(
    "div",
    { className: "metrics-heatmap-footer" },
    h(
      "div",
      { className: "metrics-heatmap-meta" },
      h(
        "span",
        { className: "metrics-heatmap-meta-item" },
        `Peak: ${peakLabel}${total > 0 ? ` - ${grid[peakDow][peakHr].toLocaleString()} docs` : ""}`,
      ),
    ),
    h(
      "div",
      { className: "metrics-heatmap-legend" },
      h("span", { className: "metrics-heatmap-legend-label" }, "less"),
      ...[0, 1, 2, 3, 4].map((i) =>
        h("div", { className: `metrics-heatmap-cell metrics-heatmap-cell--${i}` }),
      ),
      h("span", { className: "metrics-heatmap-legend-label" }, "more"),
    ),
  );

  const totalRow = h(
    "div",
    { className: "metrics-heatmap-total" },
    `Total: ${total.toLocaleString()}`,
  );

  return h(
    "div",
    { className: "metrics-chart metrics-heatmap" },
    hourLabels,
    ...rows,
    footer,
    totalRow,
  );
}

function _utcHourToLocal(utcHour, dateStr, tz) {
  const utcDate = new Date(`${dateStr}T${String(utcHour).padStart(2, "0")}:00:00Z`);
  return (
    parseInt(
      new Intl.DateTimeFormat("en-US", { hour: "numeric", hour12: false, timeZone: tz }).format(
        utcDate,
      ),
      10,
    ) % 24
  );
}

export function buildTimingChartConfig(dailyStats) {
  return {
    type: "bar",
    data: {
      labels: dailyStats.map((d) => _labelDate(d.date)),
      datasets: [
        {
          label: "Extraction (s)",
          data: dailyStats.map((d) => d.timingStats?.bdaProcessingTimeAvg ?? null),
          backgroundColor: "#3b82f6",
          borderRadius: 0,
          stack: "timing",
        },
        {
          label: "Queue (s)",
          data: dailyStats.map((d) => d.timingStats?.bdaWaitTimeAvg ?? null),
          backgroundColor: "#a5b4fc",
          borderRadius: 3,
          stack: "timing",
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: true,
          position: "bottom",
          labels: { color: "#6b7280", font: { size: 10 }, boxWidth: 12 },
        },
        tooltip: {
          mode: "index",
          callbacks: {
            footer: (items) => `Total: ${items.reduce((s, i) => s + (i.raw ?? 0), 0).toFixed(1)}s`,
          },
        },
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: "#9ca3af", font: { size: 10 }, maxTicksLimit: 10 },
          stacked: true,
        },
        y: {
          grid: { color: "#e5e7eb" },
          ticks: { color: "#9ca3af", font: { size: 10 }, callback: (v) => `${v}s` },
          beginAtZero: true,
          stacked: true,
        },
      },
    },
  };
}

export function buildDowTimingGridEl(dailyStats) {
  const DAY_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  const totals = Array.from({ length: 7 }, () => ({ ext: 0, queue: 0, total: 0, count: 0 }));

  dailyStats.forEach((d) => {
    const dow = new Date(d.date + "T00:00:00").getDay();
    const t = d.timingStats;
    if (t?.totalProcessingTimeAvg != null) {
      totals[dow].ext += t.bdaProcessingTimeAvg ?? 0;
      totals[dow].queue += t.bdaWaitTimeAvg ?? 0;
      totals[dow].total += t.totalProcessingTimeAvg;
      totals[dow].count++;
    }
  });

  const rows = totals.map(({ ext, queue, total, count }, i) =>
    count > 0
      ? {
          day: DAY_LABELS[i],
          ext: (ext / count).toFixed(1),
          queue: (queue / count).toFixed(1),
          total: (total / count).toFixed(1),
          count,
        }
      : { day: DAY_LABELS[i], ext: null, queue: null, total: null, count: 0 },
  );

  function totalColor(val) {
    if (val === null) return "";
    return val < 15 ? "timing-good" : val < 30 ? "timing-warn" : "timing-bad";
  }

  const grid = h(
    "div",
    { className: "metrics-dow-grid" },
    h("div", { className: "metrics-dow-header" }, ""),
    h("div", { className: "metrics-dow-header" }, "Extraction"),
    h("div", { className: "metrics-dow-header" }, "Queue"),
    h("div", { className: "metrics-dow-header" }, "Total"),
    ...rows.flatMap(({ day, ext, queue, total }) => [
      h("div", { className: "metrics-dow-day" }, day),
      h("div", { className: "metrics-dow-cell" }, ext !== null ? `${ext}s` : "-"),
      h("div", { className: "metrics-dow-cell" }, queue !== null ? `${queue}s` : "-"),
      h(
        "div",
        {
          className: `metrics-dow-cell metrics-dow-total ${totalColor(total !== null ? parseFloat(total) : null)}`,
        },
        total !== null ? `${total}s` : "-",
      ),
    ]),
  );

  return grid;
}

function _mountChart(container, chartRef, config, label) {
  chartRef?.destroy();
  if (label) container.appendChild(h("div", { className: "metrics-chart-label" }, label));
  const wrap = h("div", { className: "metrics-chart" });
  const canvas = document.createElement("canvas");
  wrap.appendChild(canvas);
  container.appendChild(wrap);
  return new Chart(canvas, config);
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
    multiple_documents_in_multipage: "Multiple Doc Types in Multipage",
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
