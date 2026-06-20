import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { openModal, closeModal } from "../../src/utils/modal.js";

describe("modal utility", () => {
  let modal;

  beforeEach(() => {
    modal = document.createElement("div");
    modal.classList.add("hidden");
    modal.innerHTML = `
      <input id="first" />
      <button id="middle">OK</button>
      <button id="last">Cancel</button>
    `;
    document.body.appendChild(modal);
  });

  afterEach(() => {
    closeModal(modal);
    document.body.innerHTML = "";
  });

  it("removes hidden class on open", () => {
    openModal(modal);
    expect(modal.classList.contains("hidden")).toBe(false);
  });

  it("adds hidden class on close", () => {
    openModal(modal);
    closeModal(modal);
    expect(modal.classList.contains("hidden")).toBe(true);
  });

  it("focuses first focusable element on open", () => {
    openModal(modal);
    expect(document.activeElement).toBe(modal.querySelector("#first"));
  });

  it("restores previous focus on close", () => {
    const trigger = document.createElement("button");
    document.body.appendChild(trigger);
    trigger.focus();

    openModal(modal);
    closeModal(modal);

    expect(document.activeElement).toBe(trigger);
  });

  it("ESC key closes modal", () => {
    openModal(modal);
    document.dispatchEvent(
      new KeyboardEvent("keydown", { key: "Escape", cancelable: true, bubbles: true }),
    );
    expect(modal.classList.contains("hidden")).toBe(true);
  });

  it("Tab wraps from last to first element", () => {
    openModal(modal);
    modal.querySelector("#last").focus();

    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Tab", bubbles: true }));

    expect(document.activeElement).toBe(modal.querySelector("#first"));
  });

  it("Shift+Tab wraps from first to last element", () => {
    openModal(modal);
    modal.querySelector("#first").focus();

    document.dispatchEvent(
      new KeyboardEvent("keydown", { key: "Tab", shiftKey: true, bubbles: true }),
    );

    expect(document.activeElement).toBe(modal.querySelector("#last"));
  });

  it("calls onClose callback when closed", () => {
    let called = false;
    openModal(modal, () => {
      called = true;
    });
    closeModal(modal);
    expect(called).toBe(true);
  });

  it("cleans up keydown listener after close", () => {
    openModal(modal);
    closeModal(modal);

    // ESC after close should not throw or re-close
    modal.classList.remove("hidden");
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    expect(modal.classList.contains("hidden")).toBe(false);
  });
});
