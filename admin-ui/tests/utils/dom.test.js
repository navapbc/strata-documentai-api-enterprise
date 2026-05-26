import { describe, it, expect } from "vitest";
import { h, text } from "../../src/utils/dom.js";

describe("h()", () => {
  it("creates an element with tag", () => {
    const el = h("div", null);
    expect(el.tagName).toBe("DIV");
  });

  it("sets className", () => {
    const el = h("span", { className: "badge badge-success" });
    expect(el.className).toBe("badge badge-success");
  });

  it("sets attributes", () => {
    const el = h("input", { type: "checkbox", id: "my-input" });
    expect(el.getAttribute("type")).toBe("checkbox");
    expect(el.getAttribute("id")).toBe("my-input");
  });

  it("sets data attributes", () => {
    const el = h("div", { "data-view": "keys" });
    expect(el.getAttribute("data-view")).toBe("keys");
  });

  it("appends text children as text nodes", () => {
    const el = h("td", null, "Hello", " World");
    expect(el.textContent).toBe("Hello World");
    expect(el.childNodes[0].nodeType).toBe(Node.TEXT_NODE);
  });

  it("appends element children", () => {
    const child = h("span", null, "inner");
    const el = h("div", null, child);
    expect(el.children[0].tagName).toBe("SPAN");
    expect(el.textContent).toBe("inner");
  });

  it("skips null children", () => {
    const el = h("div", null, "a", null, "b");
    expect(el.textContent).toBe("ab");
    expect(el.childNodes.length).toBe(2);
  });

  it("escapes text content (no XSS)", () => {
    const el = h("td", null, '<script>alert("xss")</script>');
    expect(el.innerHTML).toBe('&lt;script&gt;alert("xss")&lt;/script&gt;');
    expect(el.textContent).toBe('<script>alert("xss")</script>');
  });

  it("mixes text and element children", () => {
    const el = h("td", null, "Price: ", h("strong", null, "$10"));
    expect(el.childNodes.length).toBe(2);
    expect(el.textContent).toBe("Price: $10");
  });
});

describe("text()", () => {
  it("creates a text node", () => {
    const node = text("hello");
    expect(node.nodeType).toBe(Node.TEXT_NODE);
    expect(node.textContent).toBe("hello");
  });

  it("handles null", () => {
    const node = text(null);
    expect(node.textContent).toBe("");
  });
});
