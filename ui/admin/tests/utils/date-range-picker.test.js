import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { mount } from "../../src/utils/date-range-picker.js";

describe("date-range-picker", () => {
  let root, picker;

  beforeEach(() => {
    root = document.createElement("div");
    document.body.appendChild(root);
    picker = mount(root);
  });

  afterEach(() => {
    document.body.innerHTML = "";
  });

  // --- mount ---

  it("renders a preset select and hidden custom range", () => {
    expect(root.querySelector(".drp-preset")).not.toBeNull();
    expect(root.querySelector(".drp-custom").classList.contains("hidden")).toBe(true);
  });

  it("uses default placeholder text", () => {
    const first = root.querySelector(".drp-preset option[value='']");
    expect(first.textContent).toBe("Any date");
  });

  it("accepts a custom placeholder", () => {
    const r2 = document.createElement("div");
    document.body.appendChild(r2);
    mount(r2, { placeholder: "Select date range" });
    expect(r2.querySelector(".drp-preset option[value='']").textContent).toBe("Select date range");
  });

  // --- getRange ---

  it("returns null dates when no preset selected", () => {
    expect(picker.getRange()).toEqual({ dateFrom: null, dateTo: null });
  });

  it("returns yesterday for preset '1'", () => {
    root.querySelector(".drp-preset").value = "1";
    const { dateFrom, dateTo } = picker.getRange();
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);
    const expected = yesterday.toISOString().slice(0, 10);
    expect(dateFrom).toBe(expected);
    expect(dateTo).toBe(expected);
  });

  it.each([["7"], ["30"], ["90"]])("returns correct range for preset '%s'", (days) => {
    root.querySelector(".drp-preset").value = days;
    const { dateFrom, dateTo } = picker.getRange();
    const today = new Date().toISOString().slice(0, 10);
    const start = new Date();
    start.setDate(start.getDate() - parseInt(days));
    expect(dateFrom).toBe(start.toISOString().slice(0, 10));
    expect(dateTo).toBe(today);
  });

  it("returns custom inputs for preset 'custom'", () => {
    root.querySelector(".drp-preset").value = "custom";
    root.querySelector(".drp-from").value = "2026-01-01";
    root.querySelector(".drp-to").value = "2026-01-31";
    expect(picker.getRange()).toEqual({ dateFrom: "2026-01-01", dateTo: "2026-01-31" });
  });

  it("returns null for empty custom inputs", () => {
    root.querySelector(".drp-preset").value = "custom";
    expect(picker.getRange()).toEqual({ dateFrom: null, dateTo: null });
  });

  // --- custom range visibility ---

  it("shows custom inputs when preset is 'custom'", () => {
    const preset = root.querySelector(".drp-preset");
    preset.value = "custom";
    preset.dispatchEvent(new Event("change"));
    expect(root.querySelector(".drp-custom").classList.contains("hidden")).toBe(false);
  });

  it("hides custom inputs when switching away from custom", () => {
    const preset = root.querySelector(".drp-preset");
    preset.value = "custom";
    preset.dispatchEvent(new Event("change"));
    preset.value = "7";
    preset.dispatchEvent(new Event("change"));
    expect(root.querySelector(".drp-custom").classList.contains("hidden")).toBe(true);
  });

  // --- onChange ---

  it("calls onChange when preset changes", () => {
    const cb = vi.fn();
    picker.onChange(cb);
    const preset = root.querySelector(".drp-preset");
    preset.value = "7";
    preset.dispatchEvent(new Event("change"));
    expect(cb).toHaveBeenCalledOnce();
    expect(cb.mock.calls[0][0]).toMatchObject({
      dateFrom: expect.any(String),
      dateTo: expect.any(String),
    });
  });

  it("does not call onChange when switching to custom (wait for date input)", () => {
    const cb = vi.fn();
    picker.onChange(cb);
    const preset = root.querySelector(".drp-preset");
    preset.value = "custom";
    preset.dispatchEvent(new Event("change"));
    expect(cb).not.toHaveBeenCalled();
  });

  it("calls onChange when custom date inputs change", () => {
    const cb = vi.fn();
    picker.onChange(cb);
    root.querySelector(".drp-preset").value = "custom";
    const from = root.querySelector(".drp-from");
    from.value = "2026-01-01";
    from.dispatchEvent(new Event("change"));
    expect(cb).toHaveBeenCalledOnce();
  });

  it("unsubscribe stops future callbacks", () => {
    const cb = vi.fn();
    const unsub = picker.onChange(cb);
    unsub();
    root.querySelector(".drp-preset").value = "7";
    root.querySelector(".drp-preset").dispatchEvent(new Event("change"));
    expect(cb).not.toHaveBeenCalled();
  });

  // --- reset ---

  it("reset clears preset and hides custom range", () => {
    const preset = root.querySelector(".drp-preset");
    preset.value = "custom";
    preset.dispatchEvent(new Event("change"));
    root.querySelector(".drp-from").value = "2026-01-01";
    picker.reset();
    expect(preset.value).toBe("");
    expect(root.querySelector(".drp-from").value).toBe("");
    expect(root.querySelector(".drp-custom").classList.contains("hidden")).toBe(true);
  });

  // --- unmount ---

  it("unmount clears root content", () => {
    picker.unmount();
    expect(root.innerHTML).toBe("");
  });
});
