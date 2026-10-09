import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import {
  extractGeometry,
  renderBboxOverlay,
  renderPreview,
  renderExtractedData,
  markFieldsWithGeometry,
  linkFieldHighlighting,
  flattenFields,
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

    it("extracts geometry from nested field groups under dotted keys", () => {
      const fields = {
        employer: {
          address: {
            value: "123 Main St",
            geometry: [{ boundingBox: { left: 0.1, top: 0.2, width: 0.3, height: 0.04 } }],
            fieldType: "string",
          },
        },
      };
      const result = extractGeometry(fields);
      expect(result["employer.address"]).toBeDefined();
      expect(result["employer.address"].geometry).toHaveLength(1);
    });

    it("surfaces displayName for the bbox tooltip", () => {
      const fields = {
        employee_number: {
          value: "EMP-78245",
          displayName: "Employee Number",
          geometry: [{ boundingBox: { left: 0.1, top: 0.2, width: 0.3, height: 0.04 } }],
          fieldType: "string",
        },
      };
      const result = extractGeometry(fields);
      expect(result.employee_number.displayName).toBe("Employee Number");
    });
  });

  describe("flattenFields", () => {
    it("returns flat fields unchanged", () => {
      const fields = {
        name: { value: "John", confidence: 0.9 },
        age: { value: "30" },
      };
      expect(flattenFields(fields)).toEqual(fields);
    });

    it("joins nested groups into dotted keys", () => {
      const fields = {
        employer: {
          address: { value: "123 Main St", confidence: 0.77 },
          control_number: { value: "A1B2", confidence: 0.95 },
        },
        other: { value: "x", confidence: 0.94 },
      };
      expect(flattenFields(fields)).toEqual({
        "employer.address": { value: "123 Main St", confidence: 0.77 },
        "employer.control_number": { value: "A1B2", confidence: 0.95 },
        other: { value: "x", confidence: 0.94 },
      });
    });

    it("treats objects with a value/confidence/geometry key as leaves", () => {
      const leaf = {
        value: "x",
        geometry: [{ boundingBox: { left: 0, top: 0, width: 1, height: 1 } }],
      };
      expect(flattenFields({ a: { b: leaf } })).toEqual({ "a.b": leaf });
    });
  });

  describe("renderExtractedData", () => {
    it("flattens nested field groups into dotted rows", () => {
      const data = {
        employer: {
          address: { value: "123 Main St", confidence: 0.77 },
        },
        other: { value: "x", confidence: 0.94 },
      };
      const html = renderExtractedData(data, { revealed: true, maskable: false });
      expect(html).toContain("employer.address");
      expect(html).toContain("123 Main St");
      // The group must not be dumped as raw JSON.
      expect(html).not.toContain('{"address"');
    });

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

describe("image preview rotate and zoom", () => {
  let container;
  let img;
  let onRotate;

  const button = (title) =>
    [...container.querySelectorAll("button")].find((b) => b.title === title);

  // jsdom has no layout: give the image and panel real sizes so the zoom
  // math has something to work with.
  const stubSizes = ({ natW, natH, panelW }) => {
    Object.defineProperty(img, "naturalWidth", { value: natW, configurable: true });
    Object.defineProperty(img, "naturalHeight", { value: natH, configurable: true });
    Object.defineProperty(container, "clientWidth", { value: panelW, configurable: true });
  };

  beforeEach(() => {
    vi.stubGlobal("requestAnimationFrame", (fn) => fn());
    vi.stubGlobal(
      "ResizeObserver",
      class {
        observe() {}
        disconnect() {}
      },
    );
    onRotate = vi.fn();
    container = document.createElement("div");
    document.body.appendChild(container);
    renderPreview(container, {
      url: "https://example.test/doc.png",
      contentType: "image/png",
      onRotate,
    });
    img = container.querySelector("img");
  });

  afterEach(() => {
    container.remove();
    vi.unstubAllGlobals();
  });

  it("rotates right in 90 degree steps and wraps at 360", () => {
    for (const deg of [90, 180, 270, 0]) {
      button("Rotate right").click();
      expect(container._previewRotation).toBe(deg);
    }
    expect(img.style.transform).toBe("");
  });

  it("rotates left from 0 to 270", () => {
    button("Rotate left").click();
    expect(container._previewRotation).toBe(270);
    expect(img.style.transform).toBe("rotate(270deg)");
  });

  it("notifies the caller after a rotation", () => {
    button("Rotate right").click();
    expect(onRotate).toHaveBeenCalledTimes(1);
  });

  it("pads sideways images so the layout box matches the rotated footprint", () => {
    stubSizes({ natW: 1000, natH: 2000, panelW: 500 });
    button("Rotate right").click();
    // Fit by visual width: 500 wide after rotation -> 250x500 layout box.
    expect(img.style.width).toBe("250px");
    expect(img.style.height).toBe("500px");
    expect(img.style.margin).toBe("-125px 125px");
  });

  it("does not pad upright images", () => {
    stubSizes({ natW: 1000, natH: 2000, panelW: 500 });
    button("Rotate right").click();
    button("Rotate right").click();
    expect(img.style.margin).toBe("");
  });

  it("disables zoom out at fit and zoom in at the natural size", () => {
    stubSizes({ natW: 1000, natH: 2000, panelW: 500 });
    expect(button("Zoom out").disabled).toBe(true);
    expect(button("Zoom in").disabled).toBe(false);

    for (let i = 0; i < 10; i++) button("Zoom in").click();
    expect(button("Zoom in").disabled).toBe(true);
    expect(button("Zoom out").disabled).toBe(false);
    expect(img.style.width).toBe("1000px");

    for (let i = 0; i < 10; i++) button("Zoom out").click();
    expect(button("Zoom out").disabled).toBe(true);
    expect(img.style.width).toBe("");
  });

  it("caps zoom by the rotated natural size", () => {
    stubSizes({ natW: 1000, natH: 2000, panelW: 500 });
    button("Rotate right").click();
    for (let i = 0; i < 10; i++) button("Zoom in").click();
    // Sideways, the visual width is the natural height.
    expect(img.style.height).toBe("2000px");
    expect(button("Zoom in").disabled).toBe(true);
  });

  it("resets zoom when rotating", () => {
    stubSizes({ natW: 1000, natH: 2000, panelW: 500 });
    button("Zoom in").click();
    expect(container.classList.contains("preview-zoomed")).toBe(true);
    button("Rotate right").click();
    expect(container.classList.contains("preview-zoomed")).toBe(false);
    expect(button("Zoom out").disabled).toBe(true);
  });
});

describe("renderBboxOverlay", () => {
  const geometry = {
    name: {
      geometry: [{ page: 1, boundingBox: { left: 0.1, top: 0.1, width: 0.2, height: 0.05 } }],
      fieldType: "string",
    },
  };
  let container;

  beforeEach(() => {
    vi.stubGlobal(
      "ResizeObserver",
      class {
        observe() {}
        disconnect() {}
      },
    );
    container = document.createElement("div");
    document.body.appendChild(container);
  });

  afterEach(() => {
    container.remove();
    vi.unstubAllGlobals();
  });

  it("returns an inert handle when there is no geometry or no image", () => {
    container.innerHTML = '<img src="x.png" />';
    for (const [c, g] of [
      [container, null],
      [document.createElement("div"), geometry],
    ]) {
      const handle = renderBboxOverlay(c, g);
      expect(handle.observer).toBeNull();
      expect(() => handle.rerender()).not.toThrow();
    }
  });

  it("returns an observer and a rerender that rotates the overlay", () => {
    container.innerHTML = '<img src="x.png" />';
    const img = container.querySelector("img");
    Object.defineProperty(img, "complete", { value: true });
    Object.defineProperty(img, "naturalWidth", { value: 100 });

    const { observer, rerender } = renderBboxOverlay(container, geometry);
    expect(observer).not.toBeNull();
    expect(container.querySelector(".bbox-overlay-wrap").style.transform).toBe("");

    container._previewRotation = 90;
    rerender();
    const wraps = container.querySelectorAll(".bbox-overlay-wrap");
    expect(wraps).toHaveLength(1);
    expect(wraps[0].style.transform).toBe("rotate(90deg)");
  });
});
