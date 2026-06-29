import { describe, it, expect } from "vitest";
import { _fillDailyGaps } from "../../src/views/usage/usage.js";

describe("_fillDailyGaps", () => {
  it("fills all days for a past month with zeros", () => {
    const result = _fillDailyGaps("2026-01", []);
    expect(result.length).toBe(31);
    expect(result[0].date).toBe("2026-01-01");
    expect(result[30].date).toBe("2026-01-31");
    expect(result[0].total_records).toBe(0);
  });

  it("handles February (non-leap year)", () => {
    const result = _fillDailyGaps("2027-02", []);
    expect(result.length).toBe(28);
  });

  it("handles February (leap year)", () => {
    const result = _fillDailyGaps("2028-02", []);
    expect(result.length).toBe(29);
  });

  it("overlays existing data onto zero-filled days", () => {
    const existing = [
      { date: "2026-03-05", total_records: 10, total_bda_pages: 8, total_file_size_bytes: 5000, total_bedrock_input_tokens: 100, total_bedrock_output_tokens: 50 },
    ];
    const result = _fillDailyGaps("2026-03", existing);
    expect(result.length).toBe(31);
    expect(result[4].date).toBe("2026-03-05");
    expect(result[4].total_records).toBe(10);
    expect(result[3].total_records).toBe(0);
  });

  it("stops at today for current month", () => {
    const now = new Date();
    const month = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
    const result = _fillDailyGaps(month, []);
    expect(result.length).toBe(now.getDate());
  });

  it("shows all days for a past month", () => {
    const result = _fillDailyGaps("2026-04", []);
    expect(result.length).toBe(30);
    expect(result[29].date).toBe("2026-04-30");
  });
});
