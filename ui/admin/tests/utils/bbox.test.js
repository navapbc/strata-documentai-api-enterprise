import { describe, it, expect } from "vitest";
import { computeIoU, mergeOverlappingBoxes } from "../../src/utils/bbox.js";

describe("computeIoU", () => {
  it("returns 0 for disjoint boxes", () => {
    const a = { left: 0, top: 0, width: 0.1, height: 0.1 };
    const b = { left: 0.5, top: 0.5, width: 0.1, height: 0.1 };
    expect(computeIoU(a, b)).toBe(0);
  });

  it("returns 1 for identical boxes", () => {
    const a = { left: 0.2, top: 0.3, width: 0.1, height: 0.05 };
    expect(computeIoU(a, a)).toBe(1);
  });

  it("returns 0 for adjacent (touching) boxes", () => {
    const a = { left: 0, top: 0, width: 0.5, height: 0.5 };
    const b = { left: 0.5, top: 0, width: 0.5, height: 0.5 };
    expect(computeIoU(a, b)).toBe(0);
  });

  it("computes correct IoU for partially overlapping boxes", () => {
    // Two boxes: 10x10, overlapping in a 5x10 region
    const a = { left: 0, top: 0, width: 10, height: 10 };
    const b = { left: 5, top: 0, width: 10, height: 10 };
    // intersection = 5*10 = 50, union = 100+100-50 = 150
    expect(computeIoU(a, b)).toBeCloseTo(50 / 150);
  });

  it("returns > 0.5 for heavily overlapping boxes", () => {
    const a = { left: 0, top: 0, width: 1, height: 1 };
    const b = { left: 0.1, top: 0.1, width: 0.9, height: 0.9 };
    expect(computeIoU(a, b)).toBeGreaterThan(0.5);
  });

  it("returns < 0.5 for lightly overlapping boxes", () => {
    const a = { left: 0, top: 0, width: 1, height: 1 };
    const b = { left: 0.7, top: 0.7, width: 1, height: 1 };
    expect(computeIoU(a, b)).toBeLessThan(0.5);
  });
});

describe("mergeOverlappingBoxes", () => {
  it("returns single box unchanged", () => {
    const boxes = [
      { left: 0, top: 0, width: 0.1, height: 0.1, fieldName: "a", fieldType: "string" },
    ];
    const result = mergeOverlappingBoxes(boxes);
    expect(result).toHaveLength(1);
    expect(result[0].fields).toEqual([{ fieldName: "a", fieldType: "string" }]);
  });

  it("does not merge disjoint boxes", () => {
    const boxes = [
      { left: 0, top: 0, width: 0.1, height: 0.1, fieldName: "a", fieldType: "string" },
      { left: 0.5, top: 0.5, width: 0.1, height: 0.1, fieldName: "b", fieldType: "date" },
    ];
    const result = mergeOverlappingBoxes(boxes);
    expect(result).toHaveLength(2);
  });

  it("merges two heavily overlapping boxes into one", () => {
    const boxes = [
      { left: 0, top: 0, width: 1, height: 1, fieldName: "a", fieldType: "string" },
      { left: 0.1, top: 0.1, width: 0.9, height: 0.9, fieldName: "b", fieldType: "date" },
    ];
    const result = mergeOverlappingBoxes(boxes);
    expect(result).toHaveLength(1);
    expect(result[0].fields).toHaveLength(2);
    expect(result[0].fields.map((f) => f.fieldName).sort()).toEqual(["a", "b"]);
  });

  it("produces union bbox when merging", () => {
    const boxes = [
      { left: 0.1, top: 0.1, width: 0.8, height: 0.8, fieldName: "a", fieldType: "string" },
      { left: 0.2, top: 0.2, width: 0.8, height: 0.8, fieldName: "b", fieldType: "string" },
    ];
    const result = mergeOverlappingBoxes(boxes);
    expect(result).toHaveLength(1);
    expect(result[0].left).toBe(0.1);
    expect(result[0].top).toBe(0.1);
    expect(result[0].width).toBeCloseTo(0.9);
    expect(result[0].height).toBeCloseTo(0.9);
  });

  it("handles transitive merge (A overlaps B, B overlaps C, merged AB overlaps C)", () => {
    // Boxes heavily overlapping in a chain - each pair has IoU > 0.5,
    // and the union of A+B still overlaps C enough to trigger second merge
    const boxes = [
      { left: 0, top: 0, width: 1, height: 1, fieldName: "a", fieldType: "string" },
      { left: 0.2, top: 0, width: 1, height: 1, fieldName: "b", fieldType: "string" },
      { left: 0.4, top: 0, width: 1, height: 1, fieldName: "c", fieldType: "string" },
    ];
    const result = mergeOverlappingBoxes(boxes);
    expect(result).toHaveLength(1);
    expect(result[0].fields).toHaveLength(3);
  });

  it("does not merge boxes just below 0.5 IoU threshold", () => {
    // Two boxes with IoU exactly at the boundary - just under 0.5
    const a = { left: 0, top: 0, width: 1, height: 1, fieldName: "a", fieldType: "string" };
    const b = { left: 0.7, top: 0.7, width: 1, height: 1, fieldName: "b", fieldType: "string" };
    const result = mergeOverlappingBoxes([a, b]);
    expect(result).toHaveLength(2);
  });
});
