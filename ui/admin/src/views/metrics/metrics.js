import {
  Chart,
  BarController,
  DoughnutController,
  LineController,
  ArcElement,
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
import * as DateRangePicker from "../../utils/date-range-picker.js";
import { tpl } from "../../utils/tpl.js";
import { h } from "../../utils/dom.js";
import * as Icons from "../../utils/icons.js";
import html from "./metrics.html";
import {
  buildVolumeChartConfig,
  buildHourHeatmapEl,
  buildTimingChartConfig,
  buildDowTimingGridEl,
  computeBarData,
  getResponseCodeClass,
} from "./charts.js";

Chart.register(
  BarController,
  DoughnutController,
  LineController,
  ArcElement,
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
const _bodyFont = getComputedStyle(document.body).fontFamily;

let _root;
let _datePicker = null;
let _tabVolume, _tabOutcomes, _tabTiming;
let _emptyEl;
let _tenantUnsub = null;
let _loadId = 0;
let _activeTab = "volume";

export function mount(root) {
  _root = root;
  root.replaceChildren(tmpl());

  _datePicker = DateRangePicker.mount(root.querySelector("#metrics-date-range"), {
    placeholder: "Select date range",
    defaultPreset: "30",
  });
  _datePicker.onChange(() => load());

  _tabVolume = root.querySelector("#metrics-tab-volume");

  _tabOutcomes = root.querySelector("#metrics-tab-outcomes");
  _tabTiming = root.querySelector("#metrics-tab-timing");
  _emptyEl = root.querySelector("#metrics-empty");

  const validTabs = ["volume", "outcomes", "timing"];
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

  _tenantUnsub = TenantContext.onChange(() => load());
  TenantContext.mountSelect(root.querySelector("#tenant-select"));

  load();
}

export function unmount(_root) {
  if (_tenantUnsub) {
    _tenantUnsub();
    _tenantUnsub = null;
  }
  const tenantSelect = _root?.querySelector("#tenant-select");
  if (tenantSelect) TenantContext.unmountSelect(tenantSelect);
  _root = null;
}

async function load() {
  const { dateFrom: startDate, dateTo: endDate } = _datePicker.getRange();
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
    renderOutcomes(summary, summary.byClassification, summary.byResponseCode);
    renderTiming(summary.timingStats, dailyStats);
  } catch (e) {
    if (thisLoad !== _loadId) return;
    _emptyEl.textContent = `Failed to load: ${e.message}`;
    Toast.show(`Metrics load failed: ${e.message}`, "error");
  }
}

const ICONS = Icons;

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
            ctx.font = `bold 13px ${_bodyFont}`;
            ctx.fillText(stage.value.toLocaleString(), 10, yPos - 14);
            ctx.fillStyle = "#374151";
            ctx.font = `450 11px ${_bodyFont}`;
            ctx.fillText(stage.label, 10, yPos);
            if (stage.pct) {
              ctx.fillStyle = "#6b7280";
              ctx.font = `11px ${_bodyFont}`;
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

  _tabVolume.appendChild(
    h(
      "div",
      { className: "metrics-split-row" },
      buildBarCol(byFileType, "File Types", { filterNull: true }),
      buildBarCol(byUserCategory, "Tenant-Provided Document Categories", { filterNull: true }),
      buildBarCol(byUploadMethod, "Upload Methods", { filterNull: true }),
    ),
  );
}

function buildBarCol(data, label, opts = {}) {
  const bars = computeBarData(data, {
    filterNull: opts.filterNull || !opts.nullLabel,
    sortByKey: opts.sortByKey,
    nullLabel: opts.nullLabel,
  });
  const wrap = h(
    "div",
    { className: "metrics-split-third" },
    h("div", { className: "metrics-chart-label" }, label),
  );
  if (bars.length === 0) {
    wrap.appendChild(h("div", { className: "metrics-empty-hint" }, "No data"));
    return wrap;
  }
  const total = bars.reduce((s, { count }) => s + count, 0);
  wrap.appendChild(
    h(
      "div",
      { className: `metrics-panel${opts.tall ? " metrics-panel--tall" : ""}` },
      ...bars.map(({ label: l, count, widthPct }) =>
        h(
          "div",
          { className: "metrics-bar-row" },
          h("span", { className: "metrics-bar-label", title: l }, l),
          h(
            "div",
            { className: "metrics-bar-track" },
            h("div", {
              className: `metrics-bar-fill metrics-bar-fill--${opts.colorFn ? opts.colorFn(l) : "primary"}`,
              style: `width: ${widthPct}%`,
            }),
          ),
          h("span", { className: "metrics-bar-value" }, count.toLocaleString()),
        ),
      ),
      h("div", { className: "metrics-bar-total" }, `Total: ${total.toLocaleString()}`),
    ),
  );
  return wrap;
}

function renderOutcomes(summary, byClassification, byResponseCode) {
  const byCode = summary.byResponseCode || {};

  if (!byResponseCode || Object.keys(byResponseCode).length === 0) return;

  // Row 1: summary cards | response codes | (empty)
  const successCount2 = _codeCount(byCode, "0");
  const warnCount = _codeCount(byCode, "1");
  const errorCount = _codeCount(byCode, "4") + _codeCount(byCode, "9");
  const donutTotal = successCount2 + warnCount + errorCount;
  const pct = (n) => (donutTotal > 0 ? `${((n / donutTotal) * 100).toFixed(1)}%` : "");
  const donutCanvas = document.createElement("canvas");
  const donutCol = h(
    "div",
    { className: "metrics-split-third" },
    h("div", { className: "metrics-chart-label" }, "Processing Statuses"),
    h("div", { className: "metrics-panel metrics-panel--tall metrics-chart" }, donutCanvas),
  );
  new Chart(donutCanvas, {
    type: "doughnut",
    data: {
      labels: ["Success (0XX)", "Validation (1XX)", "Error (4XX/9XX)"],
      datasets: [
        {
          data: [successCount2, warnCount, errorCount],
          backgroundColor: ["#86efac", "#fde68a", "#fca5a5"],
          borderWidth: 0,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      events: ["mousemove", "mouseout"],
      plugins: {
        legend: {
          display: true,
          position: "bottom",
          labels: { color: "#6b7280", font: { size: 10 }, boxWidth: 12 },
        },
        tooltip: { enabled: true },
      },
    },
    plugins: [
      {
        afterDraw(chart) {
          const { ctx, data } = chart;
          const dataset = chart.getDatasetMeta(0);
          ctx.save();
          ctx.textAlign = "center";
          ctx.textBaseline = "middle";
          dataset.data.forEach((arc, i) => {
            const val = data.datasets[0].data[i];
            if (!val || val / donutTotal < 0.05) return;
            const label = pct(val);
            const angle = (arc.startAngle + arc.endAngle) / 2;
            const r = (arc.innerRadius + arc.outerRadius) / 2;
            const x = arc.x + Math.cos(angle) * r;
            const y = arc.y + Math.sin(angle) * r;
            ctx.fillStyle = "#111827";
            ctx.font = `11px ${_bodyFont}`;
            ctx.fillText(label, x, y);
          });
          ctx.restore();
        },
      },
    ],
  });

  _tabOutcomes.replaceChildren(
    h(
      "div",
      { className: "metrics-split-row" },
      buildBarCol(byResponseCode, "Response Codes", {
        sortByKey: true,
        colorFn: getResponseCodeClass,
        nullLabel: "No Response Code",
        tall: true,
      }),
      donutCol,
      byClassification && Object.keys(byClassification).length > 0
        ? buildBarCol(
            Object.fromEntries(
              Object.entries(byClassification).map(([k, v]) => [
                k === "null" ? "Unclassified" : k,
                v,
              ]),
            ),
            "Detected Document Types",
            { tall: true },
          )
        : h("div", { className: "metrics-split-third" }),
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
