import { describe, it, expect, beforeEach } from "vitest";
import * as Store from "../../src/state/blueprint-store.js";
import * as BlueprintList from "../../src/panes/blueprint-list.js";

describe("blueprint-list pane", () => {
  let root;

  beforeEach(() => {
    Store.reset();
    root = document.createElement("ul");
    document.body.innerHTML = "";
    document.body.appendChild(root);
  });

  it("shows loading when schemasLoading is true", () => {
    BlueprintList.mount(root);
    expect(root.textContent).toContain("Loading");
  });

  it("shows empty state when no schemas", () => {
    Store.set({ schemasLoading: false, schemas: {} });
    BlueprintList.mount(root);
    expect(root.textContent).toContain("No blueprints loaded");
  });

  it("renders doc type list from store", () => {
    Store.set({
      schemasLoading: false,
      schemas: {
        W2: [{ name: "ssn", type: "string" }],
        Payslip: [{ name: "pay", type: "number" }],
      },
    });
    BlueprintList.mount(root);
    const items = root.querySelectorAll(".nav-item");
    expect(items.length).toBe(2);
    expect(items[0].textContent).toBe("Payslip");
    expect(items[1].textContent).toBe("W2");
  });

  it("marks active doc type", () => {
    Store.set({
      schemasLoading: false,
      schemas: { W2: [], Payslip: [] },
      activeDocType: "W2",
    });
    BlueprintList.mount(root);
    const active = root.querySelector(".nav-item.active");
    expect(active.textContent).toBe("W2");
  });

  it("clicking item sets activeDocType in store", () => {
    Store.set({ schemasLoading: false, schemas: { W2: [], Payslip: [] } });
    BlueprintList.mount(root);
    root.querySelector(".nav-item").click();
    expect(Store.get().activeDocType).toBe("Payslip");
  });

  it("unmount cleans up", () => {
    const unsub = BlueprintList.mount(root);
    unsub();
    Store.set({ schemasLoading: false, schemas: { W2: [] } });
    // Should not re-render after unmount
    expect(root.innerHTML).toBe("");
  });
});

describe("blueprint-list scroll behavior", () => {
  let root;

  beforeEach(() => {
    Store.reset();
    root = document.createElement("ul");
    document.body.innerHTML = "";

    // Create the main area scroll container
    const mainArea = document.createElement("div");
    mainArea.id = "bp-main-area";
    mainArea.scrollTop = 500;
    document.body.appendChild(mainArea);
    document.body.appendChild(root);
  });

  it("scrolls main area to top when blueprint clicked", () => {
    Store.set({ schemasLoading: false, schemas: { W2: [], Payslip: [] } });
    BlueprintList.mount(root);

    const mainArea = document.querySelector("#bp-main-area");
    mainArea.scrollTop = 500;

    root.querySelector(".nav-item").click();

    expect(mainArea.scrollTop).toBe(0);
  });
});
