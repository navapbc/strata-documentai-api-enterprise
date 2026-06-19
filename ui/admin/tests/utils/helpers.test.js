import { describe, it, expect, beforeEach, vi } from "vitest";
import {
  esc,
  formatDate,
  formatDateTime,
  setViewActions,
  clearViewActions,
  showLoading,
  sortRows,
  bindSortHeaders,
} from "../../src/utils/helpers.js";

describe("esc()", () => {
  it("escapes HTML entities", () => {
    expect(esc('<script>alert("xss")</script>')).toBe('&lt;script&gt;alert("xss")&lt;/script&gt;');
  });

  it("escapes ampersands", () => {
    expect(esc("a & b")).toBe("a &amp; b");
  });

  it("handles null/undefined", () => {
    expect(esc(null)).toBe("");
    expect(esc(undefined)).toBe("");
  });

  it("passes through safe strings", () => {
    expect(esc("hello world")).toBe("hello world");
  });
});

describe("formatDate()", () => {
  it("formats ISO date", () => {
    const result = formatDate("2026-01-15T00:00:00Z");
    expect(result).toContain("2026");
  });

  it("returns dash for falsy input", () => {
    expect(formatDate(null)).toBe("-");
    expect(formatDate("")).toBe("-");
    expect(formatDate(undefined)).toBe("-");
  });
});

describe("formatDateTime()", () => {
  it("formats ISO date with time", () => {
    const result = formatDateTime("2026-01-15T13:45:30Z");
    expect(result).toContain("2026");
    // Includes a time component (hour:minute)
    expect(result).toMatch(/\d{1,2}:\d{2}/);
  });

  it("returns dash for falsy input", () => {
    expect(formatDateTime(null)).toBe("-");
    expect(formatDateTime("")).toBe("-");
    expect(formatDateTime(undefined)).toBe("-");
  });
});

describe("sortRows()", () => {
  it("returns the array unchanged when col is null", () => {
    const rows = [{ name: "b" }, { name: "a" }];
    expect(sortRows(rows, null)).toBe(rows);
  });

  it("sorts ascending by a string column", () => {
    const rows = [{ name: "charlie" }, { name: "alpha" }, { name: "bravo" }];
    expect(sortRows(rows, "name").map((r) => r.name)).toEqual(["alpha", "bravo", "charlie"]);
  });

  it("sorts descending", () => {
    const rows = [{ name: "alpha" }, { name: "charlie" }, { name: "bravo" }];
    expect(sortRows(rows, "name", "desc").map((r) => r.name)).toEqual([
      "charlie",
      "bravo",
      "alpha",
    ]);
  });

  it("sorts numerically rather than lexicographically", () => {
    const rows = [{ n: 2 }, { n: 10 }, { n: 1 }];
    expect(sortRows(rows, "n").map((r) => r.n)).toEqual([1, 2, 10]);
  });

  it("treats null/undefined values as empty strings (sorted first asc)", () => {
    const rows = [{ name: "alpha" }, { name: null }, { name: undefined }];
    const result = sortRows(rows, "name").map((r) => r.name);
    expect(result[2]).toBe("alpha");
  });

  it("does not mutate the input array", () => {
    const rows = [{ name: "b" }, { name: "a" }];
    sortRows(rows, "name");
    expect(rows.map((r) => r.name)).toEqual(["b", "a"]);
  });
});

describe("bindSortHeaders()", () => {
  let thead;

  beforeEach(() => {
    document.body.innerHTML = `<table><thead><tr>
      <th data-col="name">Name</th>
      <th>Actions</th>
    </tr></thead></table>`;
    thead = document.querySelector("thead");
  });

  it("marks th[data-col] cells as sortable", () => {
    bindSortHeaders(thead, () => {});
    const sortable = thead.querySelector('th[data-col="name"]');
    expect(sortable.classList.contains("th-sortable")).toBe(true);
    // Non-data-col headers are not marked
    expect(thead.querySelectorAll("th")[1].classList.contains("th-sortable")).toBe(false);
  });

  it("invokes onChange with asc on first click, desc on second", () => {
    const onChange = vi.fn();
    bindSortHeaders(thead, onChange);
    const th = thead.querySelector('th[data-col="name"]');

    th.click();
    expect(onChange).toHaveBeenLastCalledWith("name", "asc");
    expect(th.classList.contains("th-sort-asc")).toBe(true);

    th.click();
    expect(onChange).toHaveBeenLastCalledWith("name", "desc");
    expect(th.classList.contains("th-sort-desc")).toBe(true);
    expect(th.classList.contains("th-sort-asc")).toBe(false);
  });

  it("ignores clicks on headers without data-col", () => {
    const onChange = vi.fn();
    bindSortHeaders(thead, onChange);
    thead.querySelectorAll("th")[1].click();
    expect(onChange).not.toHaveBeenCalled();
  });

  it("returns a cleanup function that detaches the listener", () => {
    const onChange = vi.fn();
    const cleanup = bindSortHeaders(thead, onChange);
    cleanup();
    thead.querySelector('th[data-col="name"]').click();
    expect(onChange).not.toHaveBeenCalled();
  });
});

describe("setViewActions()", () => {
  beforeEach(() => {
    document.body.innerHTML = '<div id="view-actions"></div>';
  });

  it("replaces children in #view-actions", () => {
    const btn = document.createElement("button");
    btn.textContent = "Save";
    setViewActions(btn);
    const container = document.querySelector("#view-actions");
    expect(container.children.length).toBe(1);
    expect(container.children[0].textContent).toBe("Save");
  });

  it("clears previous actions", () => {
    const a = document.createElement("button");
    const b = document.createElement("button");
    setViewActions(a);
    setViewActions(b);
    const container = document.querySelector("#view-actions");
    expect(container.children.length).toBe(1);
  });

  it("accepts multiple elements", () => {
    const a = document.createElement("button");
    const b = document.createElement("select");
    setViewActions(a, b);
    const container = document.querySelector("#view-actions");
    expect(container.children.length).toBe(2);
  });
});

describe("clearViewActions()", () => {
  beforeEach(() => {
    document.body.innerHTML = '<div id="view-actions"><button>old</button></div>';
  });

  it("removes all children", () => {
    clearViewActions();
    const container = document.querySelector("#view-actions");
    expect(container.children.length).toBe(0);
  });
});

describe("showLoading()", () => {
  it("puts loading indicator in tbody and hides empty element", () => {
    document.body.innerHTML =
      '<table><tbody id="t"><tr><td>old</td></tr></tbody></table><p id="e" class="hidden"></p>';
    const tbody = document.querySelector("#t");
    const empty = document.querySelector("#e");
    showLoading(tbody, empty);
    expect(tbody.innerHTML).toContain("Loading");
    expect(empty.classList.contains("hidden")).toBe(true);
  });
});
