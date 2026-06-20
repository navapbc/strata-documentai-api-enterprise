import { describe, it, expect, beforeEach, afterEach } from "vitest";
import {
  extractGeometry,
  renderExtractedData,
  markFieldsWithGeometry,
  linkFieldHighlighting,
} from "../../shared/components/document-viewer.js";

describe("document-viewer", () => {
  describe("extractGeometry", () => {
    it("returns null for empty fields", () => {
      expect(extractGeometry({})).toBeNull();
      expect(extractGeometry(null)).toBeNull();
    });

    it("returns null when no fields have geometry", () => {
      const fields = {
        name: { value: "John", confidence: 0.95 },
        age: { value: "30", confidence: 0.8 },
      };
      expect(extractGeometry(fields)).toBeNull();
    });

    it("extracts geometry from fields that have it", () => {
      const fields = {
        name: {
          value: "John",
          confidence: 0.95,
          geometry: [{ boundingBox: { left: 0.1, top: 0.2, width: 0.3, height: 0.04 } }],
          fieldType: "string",
        },
        age: { value: "30", confidence: 0.8 },
      };

      const result = extractGeometry(fields);
      expect(result).not.toBeNull();
      expect(result.name).toBeDefined();
      expect(result.name.geometry).toHaveLength(1);
      expect(result.name.fieldType).toBe("string");
      expect(result.age).toBeUndefined();
    });

    it("defaults fieldType to unknown", () => {
      const fields = {
        name: {
          value: "John",
          geometry: [{ boundingBox: { left: 0, top: 0, width: 1, height: 1 } }],
        },
      };

      const result = extractGeometry(fields);
      expect(result.name.fieldType).toBe("unknown");
    });

    it("ignores empty geometry arrays", () => {
      const fields = {
        name: { value: "John", geometry: [] },
      };
      expect(extractGeometry(fields)).toBeNull();
    });
  });

  describe("renderExtractedData", () => {
    it("returns empty string for null data", () => {
      expect(renderExtractedData(null)).toBe("");
    });

    it("returns empty string for empty object", () => {
      expect(renderExtractedData({})).toBe("");
    });

    it("renders a table with field rows", () => {
      const data = {
        name: { value: "John", confidence: 0.95 },
        age: { value: "30", confidence: 0.72 },
      };

      const html = renderExtractedData(data, { revealed: true, maskable: false });
      expect(html).toContain("<table");
      expect(html).toContain("John");
      expect(html).toContain("30");
    });

    it("applies confidence color classes", () => {
      const data = {
        high: { value: "x", confidence: 0.95 },
        med: { value: "y", confidence: 0.75 },
        low: { value: "z", confidence: 0.5 },
      };

      const html = renderExtractedData(data, { revealed: true });
      expect(html).toContain("confidence-high");
      expect(html).toContain("confidence-med");
      expect(html).toContain("confidence-low");
    });

    it("masks values when revealed=false", () => {
      const data = {
        name: { value: "secret", confidence: 0.9 },
      };

      const html = renderExtractedData(data, { revealed: false });
      expect(html).toContain("•••••");
      // Value is in data-value attr for toggle but not displayed
      expect(html).toContain('data-value="secret"');
      expect(html).not.toContain(">secret<");
    });

    it("shows values when revealed=true", () => {
      const data = {
        name: { value: "visible", confidence: 0.9 },
      };

      const html = renderExtractedData(data, { revealed: true });
      expect(html).toContain("visible");
      expect(html).not.toContain("•••••");
    });

    it("sorts by confidence ascending", () => {
      const data = {
        high: { value: "a", confidence: 0.99 },
        low: { value: "b", confidence: 0.3 },
        mid: { value: "c", confidence: 0.7 },
      };

      const html = renderExtractedData(data, { revealed: true, maskable: false });
      const lowIdx = html.indexOf("low");
      const midIdx = html.indexOf("mid");
      const highIdx = html.indexOf("high");
      expect(lowIdx).toBeLessThan(midIdx);
      expect(midIdx).toBeLessThan(highIdx);
    });

    it("handles fields without confidence", () => {
      const data = {
        name: { value: "John" },
      };

      const html = renderExtractedData(data, { revealed: true, maskable: false });
      expect(html).toContain("John");
      expect(html).toContain("<td>-</td>");
    });
  });
});


describe("markFieldsWithGeometry", () => {
  let container;

  beforeEach(() => {
    container = document.createElement("div");
    container.innerHTML = `
      <table><tbody>
        <tr data-field="name"><td>name</td></tr>
        <tr data-field="age"><td>age</td></tr>
        <tr data-field="address"><td>address</td></tr>
      </tbody></table>
    `;
  });

  it("adds has-geometry class to rows with geometry", () => {
    const geo = {
      name: { geometry: [{ boundingBox: {} }], fieldType: "string" },
    };

    markFieldsWithGeometry(container, geo);

    const nameRow = container.querySelector('tr[data-field="name"]');
    const ageRow = container.querySelector('tr[data-field="age"]');
    expect(nameRow.classList.contains("has-geometry")).toBe(true);
    expect(ageRow.classList.contains("has-geometry")).toBe(false);
  });

  it("sets --field-color CSS variable from fieldType", () => {
    const geo = {
      name: { geometry: [{ boundingBox: {} }], fieldType: "string" },
      age: { geometry: [{ boundingBox: {} }], fieldType: "number" },
    };

    markFieldsWithGeometry(container, geo);

    const nameRow = container.querySelector('tr[data-field="name"]');
    const ageRow = container.querySelector('tr[data-field="age"]');
    expect(nameRow.style.getPropertyValue("--field-color")).toBe("#44aaff");
    expect(ageRow.style.getPropertyValue("--field-color")).toBe("#ff8c00");
  });

  it("removes has-geometry and --field-color when geometry is null", () => {
    markFieldsWithGeometry(container, {
      name: { geometry: [{ boundingBox: {} }], fieldType: "string" },
    });

    markFieldsWithGeometry(container, null);

    const nameRow = container.querySelector('tr[data-field="name"]');
    expect(nameRow.classList.contains("has-geometry")).toBe(false);
    expect(nameRow.style.getPropertyValue("--field-color")).toBe("");
  });
});

describe("linkFieldHighlighting", () => {
  let tableContainer, previewContainer;
  let originalScrollIntoView;

  beforeEach(() => {
    // jsdom doesn't support scrollIntoView on SVG elements
    originalScrollIntoView = Element.prototype.scrollIntoView;
    Element.prototype.scrollIntoView = () => {};

    tableContainer = document.createElement("div");
    tableContainer.innerHTML = `
      <table><tbody>
        <tr data-field="name"><td>name</td></tr>
        <tr data-field="age"><td>age</td></tr>
      </tbody></table>
    `;

    previewContainer = document.createElement("div");
    previewContainer.innerHTML = `
      <svg class="bbox-overlay">
        <rect data-fields="name"></rect>
        <rect data-fields="age"></rect>
      </svg>
    `;

    document.body.appendChild(tableContainer);
    document.body.appendChild(previewContainer);
  });

  afterEach(() => {
    document.body.removeChild(tableContainer);
    document.body.removeChild(previewContainer);
    Element.prototype.scrollIntoView = originalScrollIntoView;
  });

  it("highlights box when hovering a field row", () => {
    linkFieldHighlighting(tableContainer, previewContainer);

    const nameRow = tableContainer.querySelector('tr[data-field="name"]');
    nameRow.dispatchEvent(new MouseEvent("mouseover", { bubbles: true }));

    const nameRect = previewContainer.querySelector('rect[data-fields="name"]');
    const ageRect = previewContainer.querySelector('rect[data-fields="age"]');
    expect(nameRect.classList.contains("bbox-highlight")).toBe(true);
    expect(ageRect.classList.contains("bbox-highlight")).toBe(false);
  });

  it("clears box highlights on table mouseleave", () => {
    linkFieldHighlighting(tableContainer, previewContainer);

    const nameRow = tableContainer.querySelector('tr[data-field="name"]');
    nameRow.dispatchEvent(new MouseEvent("mouseover", { bubbles: true }));
    tableContainer.dispatchEvent(new MouseEvent("mouseleave", { bubbles: true }));

    const nameRect = previewContainer.querySelector('rect[data-fields="name"]');
    expect(nameRect.classList.contains("bbox-highlight")).toBe(false);
  });

  it("highlights row when hovering a box", () => {
    linkFieldHighlighting(tableContainer, previewContainer);

    const nameRect = previewContainer.querySelector('rect[data-fields="name"]');
    nameRect.dispatchEvent(new MouseEvent("mouseover", { bubbles: true }));

    const nameRow = tableContainer.querySelector('tr[data-field="name"]');
    const ageRow = tableContainer.querySelector('tr[data-field="age"]');
    expect(nameRow.classList.contains("row-highlight")).toBe(true);
    expect(ageRow.classList.contains("row-highlight")).toBe(false);
  });

  it("clears row highlights on preview mouseleave", () => {
    linkFieldHighlighting(tableContainer, previewContainer);

    const nameRect = previewContainer.querySelector('rect[data-fields="name"]');
    nameRect.dispatchEvent(new MouseEvent("mouseover", { bubbles: true }));
    previewContainer.dispatchEvent(new MouseEvent("mouseleave", { bubbles: true }));

    const nameRow = tableContainer.querySelector('tr[data-field="name"]');
    expect(nameRow.classList.contains("row-highlight")).toBe(false);
  });
});
