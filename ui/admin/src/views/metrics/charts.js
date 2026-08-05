import { h } from "../../utils/dom.js";
const _bodyFont = getComputedStyle(document.body).fontFamily;

function _labelDate(dateStr) {
  const [, m, d] = dateStr.split("-");
  return `${parseInt(m)}/${parseInt(d)}`;
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
          ticks: { color: "#9ca3af", font: { family: _bodyFont, size: 10 }, maxTicksLimit: 10 },
        },
        y: {
          grid: { display: false },
          ticks: { color: "#9ca3af", font: { family: _bodyFont, size: 10 } },
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
          ctx.font = `10px ${_bodyFont}`;
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
    h("div", { className: "metrics-hour-day-label" }),
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
          labels: { color: "#6b7280", font: { family: _bodyFont, size: 10 }, boxWidth: 12 },
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
          ticks: { color: "#9ca3af", font: { family: _bodyFont, size: 10 }, maxTicksLimit: 10 },
          stacked: true,
        },
        y: {
          grid: { color: "#e5e7eb" },
          ticks: {
            color: "#9ca3af",
            font: { family: _bodyFont, size: 10 },
            callback: (v) => `${v}s`,
          },
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

  return h(
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
}

export function computeBarData(
  entries,
  { filterNull = false, sortByKey = false, nullLabel = null } = {},
) {
  let items = Object.entries(entries);
  if (filterNull) items = items.filter(([k]) => k !== "null");
  else if (nullLabel) items = items.map(([k, v]) => [k === "null" ? nullLabel : k, v]);
  if (sortByKey) items.sort((a, b) => a[0].localeCompare(b[0]));
  else items.sort((a, b) => b[1] - a[1]);
  const max = items.length > 0 ? Math.max(...items.map(([, c]) => c)) : 1;
  return items.map(([label, count]) => ({
    label,
    count,
    widthPct: (count / max) * 100,
  }));
}

export function getResponseCodeClass(code) {
  if (code.startsWith("000")) return "success";
  if (code.startsWith("0")) return "warn";
  if (code.startsWith("1")) return "warn";
  return "danger";
}
