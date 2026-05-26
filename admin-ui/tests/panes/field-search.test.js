import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";

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
    input.value = "ssn";
    input.dispatchEvent(new Event("input"));

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

    input.value = "";
    input.dispatchEvent(new Event("input"));
    await vi.advanceTimersByTimeAsync(200);

    expect(results.innerHTML).toBe("");
  });

  it("no matches shows empty state", async () => {
    FieldSearch.mount(root);
    const input = root.querySelector("#bp-field-search");
    input.value = "zzzzz";
    input.dispatchEvent(new Event("input"));
    await vi.advanceTimersByTimeAsync(200);

    const results = document.querySelector("#bp-search-results");
    expect(results.querySelector(".empty-state")).toBeTruthy();
  });
});
