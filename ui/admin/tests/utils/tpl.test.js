import { describe, it, expect } from "vitest";
import { tpl } from "../../src/utils/tpl.js";

describe("tpl()", () => {
  it("returns a function", () => {
    const render = tpl("<div>hello</div>");
    expect(typeof render).toBe("function");
  });

  it("returns a DocumentFragment on each call", () => {
    const render = tpl("<p>test</p>");
    const frag = render();
    expect(frag).toBeInstanceOf(DocumentFragment);
    expect(frag.querySelector("p").textContent).toBe("test");
  });

  it("returns independent clones", () => {
    const render = tpl('<input id="x" />');
    const a = render();
    const b = render();
    const inputA = a.querySelector("#x");
    const inputB = b.querySelector("#x");
    inputA.value = "changed";
    expect(inputB.value).toBe("");
  });

  it("preserves complex HTML structure", () => {
    const render = tpl(`
      <div class="wrapper">
        <h2>Title</h2>
        <ul><li>One</li><li>Two</li></ul>
      </div>
    `);
    const frag = render();
    expect(frag.querySelector(".wrapper")).not.toBeNull();
    expect(frag.querySelectorAll("li").length).toBe(2);
  });
});
