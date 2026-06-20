import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { typeInto } from "../helpers.js";

let FieldSearch, Store, mockRulesGet, mockRulesPut, mockGetTenantId;

describe("field-search pane", () => {
  let root;

  beforeEach(async () => {
    vi.resetModules();
    vi.useFakeTimers();

    mockRulesGet = vi
      .fn()
      .mockResolvedValue({ rules: [{ requiredFields: ["ssn"], optionalFields: ["name"] }] });
    mockRulesPut = vi.fn().mockResolvedValue({});
    mockGetTenantId = vi.fn().mockReturnValue("acme");

    vi.doMock("../../src/services/rules.js", () => ({
      get: mockRulesGet,
      put: mockRulesPut,
    }));
    vi.doMock("../../src/utils/tenant-context.js", () => ({
      getTenantId: mockGetTenantId,
      onChange: vi.fn(() => () => {}),
    }));
    vi.doMock("../../src/utils/toast.js", () => ({
      show: vi.fn(),
    }));

    Store = await import("../../src/state/blueprint-store.js");
    FieldSearch = await import("../../src/panes/field-search.js");

    root = document.createElement("div");
    // Create search results container in document
    const results = document.createElement("div");
    results.id = "bp-search-results";
    document.body.appendChild(results);

    // Create save/discard buttons
    const saveBtn = document.createElement("button");
    saveBtn.id = "bp-save-btn";
    saveBtn.classList.add("hidden");
    document.body.appendChild(saveBtn);

    const discardBtn = document.createElement("button");
    discardBtn.id = "bp-discard-btn";
    discardBtn.classList.add("hidden");
    document.body.appendChild(discardBtn);

    // Seed store with schemas
    Store.set({
      schemas: {
        W2: [
          { name: "ssn", type: "string" },
          { name: "wages", type: "number" },
        ],
        I9: [
          { name: "ssn", type: "string" },
          { name: "citizenship", type: "string" },
        ],
      },
    });
  });

  afterEach(() => {
    vi.useRealTimers();
    document.body.innerHTML = "";
    Store.reset();
  });

  it("mounts with search input", () => {
    FieldSearch.mount(root);
    expect(root.querySelector("#bp-field-search")).toBeTruthy();
  });

  it("search finds matching fields across doc types", async () => {
    FieldSearch.mount(root);
    const input = root.querySelector("#bp-field-search");
    typeInto(input, "ssn");

    await vi.advanceTimersByTimeAsync(200);
    // Wait for async renderResults
    await vi.runAllTimersAsync();

    const results = document.querySelector("#bp-search-results");
    const groups = results.querySelectorAll(".search-group");
    expect(groups.length).toBe(2); // W2 and I9 both have ssn
  });

  it("empty search clears results", async () => {
    FieldSearch.mount(root);
    const input = root.querySelector("#bp-field-search");
    const results = document.querySelector("#bp-search-results");
    results.innerHTML = "<p>old</p>";

    typeInto(input, "");
    await vi.advanceTimersByTimeAsync(200);

    expect(results.innerHTML).toBe("");
  });

  it("no matches shows empty state", async () => {
    FieldSearch.mount(root);
    const input = root.querySelector("#bp-field-search");
    typeInto(input, "zzzzz");
    await vi.advanceTimersByTimeAsync(200);

    const results = document.querySelector("#bp-search-results");
    expect(results.querySelector(".empty-state")).toBeTruthy();
  });
});

describe("field-search clears on blueprint selection", () => {
  let root, FieldSearch, Store;

  beforeEach(async () => {
    vi.resetModules();
    vi.useFakeTimers();

    vi.doMock("../../src/services/rules.js", () => ({
      get: vi.fn().mockResolvedValue({ rules: [] }),
      put: vi.fn().mockResolvedValue({}),
    }));
    vi.doMock("../../src/utils/tenant-context.js", () => ({
      getTenantId: vi.fn(() => "acme"),
      onChange: vi.fn(() => () => {}),
    }));
    vi.doMock("../../src/utils/toast.js", () => ({ show: vi.fn() }));

    Store = await import("../../src/state/blueprint-store.js");
    FieldSearch = await import("../../src/panes/field-search.js");

    root = document.createElement("div");
    const results = document.createElement("div");
    results.id = "bp-search-results";
    document.body.appendChild(results);

    const editor = document.createElement("div");
    editor.id = "extraction-rule-editor-pane";
    document.body.appendChild(editor);

    const saveBtn = document.createElement("button");
    saveBtn.id = "bp-save-btn";
    document.body.appendChild(saveBtn);

    const discardBtn = document.createElement("button");
    discardBtn.id = "bp-discard-btn";
    document.body.appendChild(discardBtn);

    Store.set({
      schemas: {
        W2: [{ name: "ssn", type: "string" }],
        I9: [{ name: "ssn", type: "string" }],
      },
    });
  });

  afterEach(() => {
    vi.useRealTimers();
    document.body.innerHTML = "";
    Store.reset();
  });

  it("clears search input when activeDocType is set", async () => {
    FieldSearch.mount(root);
    const input = root.querySelector("#bp-field-search");
    typeInto(input, "ssn");
    await vi.advanceTimersByTimeAsync(200);
    await vi.runAllTimersAsync();

    // Simulate blueprint click
    Store.set({ activeDocType: "W2" });

    expect(input.value).toBe("");
  });

  it("clears search results when activeDocType is set", async () => {
    FieldSearch.mount(root);
    const input = root.querySelector("#bp-field-search");
    typeInto(input, "ssn");
    await vi.advanceTimersByTimeAsync(200);
    await vi.runAllTimersAsync();

    const results = document.querySelector("#bp-search-results");
    expect(results.children.length).toBeGreaterThan(0);

    Store.set({ activeDocType: "W2" });

    expect(results.children.length).toBe(0);
  });

  it("unhides editor pane when activeDocType is set", async () => {
    FieldSearch.mount(root);
    const editor = document.querySelector("#extraction-rule-editor-pane");
    editor.classList.add("hidden");

    const input = root.querySelector("#bp-field-search");
    input.value = "ssn";

    Store.set({ activeDocType: "W2" });

    expect(editor.classList.contains("hidden")).toBe(false);
  });
});

describe("field-search does not modify view-title", () => {
  let root, FieldSearch, Store;

  beforeEach(async () => {
    vi.resetModules();
    vi.useFakeTimers();

    vi.doMock("../../src/services/rules.js", () => ({
      get: vi.fn().mockResolvedValue({ rules: [] }),
      put: vi.fn().mockResolvedValue({}),
    }));
    vi.doMock("../../src/utils/tenant-context.js", () => ({
      getTenantId: vi.fn(() => "acme"),
      onChange: vi.fn(() => () => {}),
    }));
    vi.doMock("../../src/utils/toast.js", () => ({ show: vi.fn() }));

    Store = await import("../../src/state/blueprint-store.js");
    FieldSearch = await import("../../src/panes/field-search.js");

    root = document.createElement("div");
    const results = document.createElement("div");
    results.id = "bp-search-results";
    document.body.appendChild(results);

    const title = document.createElement("h2");
    title.id = "view-title";
    title.textContent = "Manage Extraction Rules";
    document.body.appendChild(title);

    Store.set({ schemas: { W2: [{ name: "ssn", type: "string" }] } });
  });

  afterEach(() => {
    vi.useRealTimers();
    document.body.innerHTML = "";
    Store.reset();
  });

  it("does not change view-title on search", async () => {
    FieldSearch.mount(root);
    const input = root.querySelector("#bp-field-search");
    typeInto(input, "ssn");
    await vi.advanceTimersByTimeAsync(200);

    expect(document.querySelector("#view-title").textContent).toBe("Manage Extraction Rules");
  });

  it("does not change view-title on clear", async () => {
    FieldSearch.mount(root);
    const input = root.querySelector("#bp-field-search");
    typeInto(input, "ssn");
    await vi.advanceTimersByTimeAsync(200);

    typeInto(input, "");
    await vi.advanceTimersByTimeAsync(200);

    expect(document.querySelector("#view-title").textContent).toBe("Manage Extraction Rules");
  });
});
