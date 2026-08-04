import { describe, it, expect, beforeAll, vi } from "vitest";

vi.mock("chart.js", () => ({
  Chart: Object.assign(vi.fn(), { register: vi.fn() }),
  BarController: {},
  LineController: {},
  BarElement: {},
  LineElement: {},
  PointElement: {},
  CategoryScale: {},
  LinearScale: {},
  Tooltip: {},
  Filler: {},
}));
import {
  _statusColor,
  _humanizeStatus,
  _codeColor,
  computeBarData,
  buildVolumeChartConfig,
  buildTimingChartConfig,
} from "../../src/views/metrics/metrics.js";

beforeAll(() => {
  // jsdom doesn't implement createElementNS SVG fully but enough for attribute checks
  if (!globalThis.document) return;
});

describe("_statusColor", () => {
  it("returns success for Success", () => {
    expect(_statusColor("Success")).toBe("success");
  });

  it("returns danger for Failed", () => {
    expect(_statusColor("Failed")).toBe("danger");
  });

  it("returns neutral for other statuses", () => {
    expect(_statusColor("No Document Detected")).toBe("neutral");
    expect(_statusColor("Blurry Document")).toBe("neutral");
  });
});

describe("_humanizeStatus", () => {
  it("maps known statuses", () => {
    expect(_humanizeStatus("success")).toBe("Success");
    expect(_humanizeStatus("failed")).toBe("Failed");
    expect(_humanizeStatus("no_document_detected")).toBe("No Document Detected");
    expect(_humanizeStatus("no_custom_blueprint_matched")).toBe("No Blueprint Matched");
    expect(_humanizeStatus("multiple_documents_single_page")).toBe("Multiple Documents");
    expect(_humanizeStatus("ai_consent_declined")).toBe("AI Consent Declined");
    expect(_humanizeStatus("conversion_failed")).toBe("Conversion Failed");
    expect(_humanizeStatus("password_protected")).toBe("Password Protected");
    expect(_humanizeStatus("blurry_document_detected")).toBe("Blurry Document");
  });

  it("falls back to title case for unknown statuses", () => {
    expect(_humanizeStatus("some_new_status")).toBe("Some New Status");
  });
});

describe("_codeColor", () => {
  it("returns success for 000 codes", () => {
    expect(_codeColor("000 - Document validation passed")).toBe("success");
  });

  it("returns warn for other 0xx codes", () => {
    expect(_codeColor("001 - Bitmap received")).toBe("warn");
    expect(_codeColor("002 - Type not implemented")).toBe("warn");
  });

  it("returns warn for 1xx codes", () => {
    expect(_codeColor("101 - Missing fields")).toBe("warn");
    expect(_codeColor("103 - No document detected")).toBe("warn");
    expect(_codeColor("104 - Blurry document")).toBe("warn");
  });

  it("returns danger for 4xx and 999 codes", () => {
    expect(_codeColor("400 - Multiple documents")).toBe("danger");
    expect(_codeColor("999 - Internal error")).toBe("danger");
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
  it("returns a line chart config", () => {
    const config = buildTimingChartConfig(DAILY_STATS);
    expect(config.type).toBe("line");
  });

  it("has 3 datasets (end-to-end, extraction, queue)", () => {
    const config = buildTimingChartConfig(DAILY_STATS);
    expect(config.data.datasets).toHaveLength(3);
  });

  it("maps timing fields correctly", () => {
    const config = buildTimingChartConfig(DAILY_STATS);
    expect(config.data.datasets[0].data).toEqual([5, 6, 4]); // totalProcessingTimeAvg
    expect(config.data.datasets[1].data).toEqual([3, 4, 2]); // bdaProcessingTimeAvg
    expect(config.data.datasets[2].data).toEqual([1, 2, 1]); // bdaWaitTimeAvg
  });

  it("uses the same labels as volume chart", () => {
    const config = buildTimingChartConfig(DAILY_STATS);
    expect(config.data.labels).toEqual(["1/1", "1/2", "1/3"]);
  });
});
