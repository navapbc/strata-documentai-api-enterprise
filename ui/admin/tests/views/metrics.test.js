import { describe, it, expect, beforeAll, beforeEach, afterEach, vi } from "vitest";

vi.mock("chart.js", () => ({
  Chart: Object.assign(vi.fn(), { register: vi.fn() }),
  BarController: {},
  DoughnutController: {},
  LineController: {},
  ArcElement: {},
  BarElement: {},
  LineElement: {},
  PointElement: {},
  CategoryScale: {},
  LinearScale: {},
  Tooltip: {},
  Legend: {},
  Filler: {},
}));
import {
  computeBarData,
  buildVolumeChartConfig,
  buildTimingChartConfig,
  getResponseCodeClass,
} from "../../src/views/metrics/charts.js";

beforeAll(() => {
  // jsdom doesn't implement createElementNS SVG fully but enough for attribute checks
  if (!globalThis.document) return;
});

describe("getResponseCodeClass", () => {
  it("returns success for 000 codes", () => {
    expect(getResponseCodeClass("000 - Document validation passed")).toBe("success");
  });

  it("returns warn for other 0xx codes", () => {
    expect(getResponseCodeClass("001 - Bitmap received")).toBe("warn");
    expect(getResponseCodeClass("002 - Type not implemented")).toBe("warn");
  });

  it("returns warn for 1xx codes", () => {
    expect(getResponseCodeClass("101 - Missing fields")).toBe("warn");
    expect(getResponseCodeClass("103 - No document detected")).toBe("warn");
  });

  it("returns danger for 4xx and 9xx codes", () => {
    expect(getResponseCodeClass("400 - Multiple documents")).toBe("danger");
    expect(getResponseCodeClass("999 - Internal error")).toBe("danger");
  });
});

describe("computeBarData", () => {
  it("widths never exceed 100%", () => {
    const data = { "000 - Success": 500, "101 - Missing": 50, "999 - Error": 3 };
    const bars = computeBarData(data);
    bars.forEach(({ widthPct }) => {
      expect(widthPct).toBeLessThanOrEqual(100);
      expect(widthPct).toBeGreaterThan(0);
    });
  });

  it("max count gets 100% width", () => {
    const data = { a: 100, b: 50, c: 25 };
    const bars = computeBarData(data);
    const maxBar = bars.find((b) => b.count === 100);
    expect(maxBar.widthPct).toBe(100);
  });

  it("filters null entries when filterNull is true", () => {
    const data = { "000 - Success": 10, null: 5, "101 - Missing": 3 };
    const bars = computeBarData(data, { filterNull: true });
    expect(bars.find((b) => b.label === "null")).toBeUndefined();
    expect(bars.length).toBe(2);
  });

  it("keeps null entries when filterNull is false", () => {
    const data = { "000 - Success": 10, null: 5 };
    const bars = computeBarData(data, { filterNull: false });
    expect(bars.find((b) => b.label === "null")).toBeDefined();
  });

  it("sorts by key when sortByKey is true", () => {
    const data = { "101 - Missing": 50, "000 - Success": 500 };
    const bars = computeBarData(data, { sortByKey: true });
    expect(bars[0].label).toBe("000 - Success");
    expect(bars[1].label).toBe("101 - Missing");
  });

  it("sorts by count descending by default", () => {
    const data = { a: 10, b: 100, c: 50 };
    const bars = computeBarData(data);
    expect(bars[0].count).toBe(100);
    expect(bars[1].count).toBe(50);
    expect(bars[2].count).toBe(10);
  });

  it("handles empty input", () => {
    const bars = computeBarData({});
    expect(bars).toEqual([]);
  });

  it("max uses largest count not first alphabetical entry", () => {
    const data = { "999 - Error": 200, "000 - Success": 50 };
    const bars = computeBarData(data, { sortByKey: true });
    // 000 is first alphabetically but has lower count
    const firstBar = bars[0];
    expect(firstBar.label).toBe("000 - Success");
    expect(firstBar.widthPct).toBe(25); // 50/200 * 100
    const secondBar = bars[1];
    expect(secondBar.widthPct).toBe(100); // 200/200 * 100
  });
});

const DAILY_STATS = [
  {
    date: "2024-01-01",
    totalRecords: 10,
    timingStats: { totalProcessingTimeAvg: 5, bdaProcessingTimeAvg: 3, bdaWaitTimeAvg: 1 },
  },
  {
    date: "2024-01-02",
    totalRecords: 20,
    timingStats: { totalProcessingTimeAvg: 6, bdaProcessingTimeAvg: 4, bdaWaitTimeAvg: 2 },
  },
  {
    date: "2024-01-03",
    totalRecords: 15,
    timingStats: { totalProcessingTimeAvg: 4, bdaProcessingTimeAvg: 2, bdaWaitTimeAvg: 1 },
  },
];

describe("buildVolumeChartConfig", () => {
  it("returns a bar chart config", () => {
    const config = buildVolumeChartConfig(DAILY_STATS);
    expect(config.type).toBe("bar");
  });

  it("has one dataset with correct data length", () => {
    const config = buildVolumeChartConfig(DAILY_STATS);
    expect(config.data.datasets).toHaveLength(1);
    expect(config.data.datasets[0].data).toHaveLength(DAILY_STATS.length);
  });

  it("maps totalRecords to dataset values", () => {
    const config = buildVolumeChartConfig(DAILY_STATS);
    expect(config.data.datasets[0].data).toEqual([10, 20, 15]);
  });

  it("formats labels as M/D", () => {
    const config = buildVolumeChartConfig(DAILY_STATS);
    expect(config.data.labels).toEqual(["1/1", "1/2", "1/3"]);
  });
});

describe("buildTimingChartConfig", () => {
  it("returns a bar chart config", () => {
    const config = buildTimingChartConfig(DAILY_STATS);
    expect(config.type).toBe("bar");
  });

  it("has 2 datasets (extraction, queue)", () => {
    const config = buildTimingChartConfig(DAILY_STATS);
    expect(config.data.datasets).toHaveLength(2);
  });

  it("maps timing fields correctly", () => {
    const config = buildTimingChartConfig(DAILY_STATS);
    expect(config.data.datasets[0].data).toEqual([3, 4, 2]); // bdaProcessingTimeAvg
    expect(config.data.datasets[1].data).toEqual([1, 2, 1]); // bdaWaitTimeAvg
  });

  it("uses the same labels as volume chart", () => {
    const config = buildTimingChartConfig(DAILY_STATS);
    expect(config.data.labels).toEqual(["1/1", "1/2", "1/3"]);
  });
});

describe("metrics view date format", () => {
  let root, mockGet;

  beforeEach(async () => {
    vi.resetModules();
    mockGet = vi.fn().mockResolvedValue({ summary: null, dailyStats: [] });
    vi.doMock("../../src/services/metrics.js", () => ({ get: mockGet }));
    vi.doMock("../../src/utils/tenant-context.js", () => ({
      getTenantId: vi.fn(() => null),
      onChange: vi.fn(() => () => {}),
    }));
    vi.doMock("../../src/utils/toast.js", () => ({ show: vi.fn() }));
    vi.doMock("../../src/utils/helpers.js", () => ({}));
    root = document.createElement("div");
    document.body.appendChild(root);
    const MetricsView = await import("../../src/views/metrics/metrics.js");
    MetricsView.mount(root);
    await new Promise((r) => setTimeout(r, 0));
  });

  afterEach(() => {
    document.body.innerHTML = "";
  });

  it("sends bare YYYY-MM-DD dates to metrics service (not ISO timestamps)", () => {
    expect(mockGet).toHaveBeenCalled();
    const { startDate, endDate } = mockGet.mock.calls[0][0];
    expect(startDate).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    expect(endDate).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });
});
