import { describe, it, expect, beforeEach, afterEach } from "vitest";
import * as Store from "../../src/state/blueprint-store.js";
import * as BlueprintList from "../../src/panes/blueprint-list.js";

describe("blueprint-list pane", () => {
  let root;

  beforeEach(() => {
    Store.reset();
    root = document.createElement("div");
    document.body.innerHTML = "";
    document.body.appendChild(root);
  });

  afterEach(() => {
    document.body.innerHTML = "";
    Store.reset();
  });

  it("mounts and renders combobox input", () => {
    BlueprintList.mount(root);
    expect(root.querySelector(".combobox-input")).not.toBeNull();
  });

  it("sets items from store schemas", () => {
    Store.set({
      schemasLoading: false,
      schemas: {
        W2: [{ name: "ssn", type: "string" }],
        Payslip: [{ name: "pay", type: "number" }],
      },
    });
    BlueprintList.mount(root);
    // Open the dropdown
    root.querySelector(".combobox-input").dispatchEvent(new Event("click"));
    const options = root.querySelectorAll(".combobox-option");
    expect(options.length).toBe(2);
    expect(options[0].textContent).toBe("Payslip");
    expect(options[1].textContent).toBe("W2");
  });

  it("sets input value from activeDocType", () => {
    Store.set({
      schemasLoading: false,
      schemas: { W2: [], Payslip: [] },
      activeDocType: "W2",
    });
    BlueprintList.mount(root);
    expect(root.querySelector(".combobox-input").value).toBe("W2");
  });

  it("selecting item sets activeDocType in store", () => {
    Store.set({ schemasLoading: false, schemas: { W2: [], Payslip: [] } });
    BlueprintList.mount(root);
    root.querySelector(".combobox-input").dispatchEvent(new Event("click"));
    root
      .querySelector(".combobox-option")
      .dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
    expect(Store.get().activeDocType).toBe("Payslip");
  });

  it("unmount cleans up", () => {
    const unsub = BlueprintList.mount(root);
    unsub();
    expect(root.children.length).toBe(0);
  });
});

describe("blueprint-list scroll behavior", () => {
  let root, mainArea;

  beforeEach(() => {
    Store.reset();
    root = document.createElement("div");
    mainArea = document.createElement("div");
    mainArea.id = "bp-main-area";
    document.body.innerHTML = "";
    document.body.appendChild(root);
    document.body.appendChild(mainArea);
  });

  afterEach(() => {
    document.body.innerHTML = "";
    Store.reset();
  });

  it("scrolls main area to top when blueprint selected", () => {
    Store.set({ schemasLoading: false, schemas: { W2: [], Payslip: [] } });
    BlueprintList.mount(root);
    mainArea.scrollTop = 500;

    root.querySelector(".combobox-input").dispatchEvent(new Event("click"));
    root
      .querySelector(".combobox-option")
      .dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));

    expect(mainArea.scrollTop).toBe(0);
  });
});
