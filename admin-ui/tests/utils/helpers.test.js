import { describe, it, expect, beforeEach } from "vitest";
import {
  esc,
  formatDate,
  setViewActions,
  clearViewActions,
  showLoading,
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
  it("clears tbody and shows loading in empty element", () => {
    document.body.innerHTML =
      '<table><tbody id="t"><tr><td>old</td></tr></tbody></table><p id="e" class="hidden"></p>';
    const tbody = document.querySelector("#t");
    const empty = document.querySelector("#e");
    showLoading(tbody, empty);
    expect(tbody.innerHTML).toBe("");
    expect(empty.textContent).toBe("Loading…");
    expect(empty.classList.contains("hidden")).toBe(false);
  });
});
