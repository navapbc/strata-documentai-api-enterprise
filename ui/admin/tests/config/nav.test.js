import { describe, it, expect } from "vitest";
import NAV_SECTIONS from "../../src/config/nav.js";

describe("nav config", () => {
  it("every section has required fields", () => {
    NAV_SECTIONS.forEach((section) => {
      expect(section.id).toBeTruthy();
      expect(section.label).toBeTruthy();
      expect(section.icon).toBeTruthy();
      expect(section.description).toBeTruthy();
      expect(Array.isArray(section.items)).toBe(true);
      expect(section.items.length).toBeGreaterThan(0);
    });
  });

  it("every item has a view and label", () => {
    NAV_SECTIONS.flatMap((s) => s.items).forEach((item) => {
      expect(item.view).toBeTruthy();
      expect(item.label).toBeTruthy();
    });
  });

  it("all view values are unique", () => {
    const views = NAV_SECTIONS.flatMap((s) => s.items).map((i) => i.view);
    expect(views.length).toBe(new Set(views).size);
  });

  it("all section ids are unique", () => {
    const ids = NAV_SECTIONS.map((s) => s.id);
    expect(ids.length).toBe(new Set(ids).size);
  });
});
