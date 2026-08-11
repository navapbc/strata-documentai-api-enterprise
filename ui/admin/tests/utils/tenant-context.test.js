import { describe, it, expect, beforeEach, vi } from "vitest";
import * as TenantContext from "../../src/utils/tenant-context.js";

vi.mock("../../src/services/tenants.js", () => ({
  list: vi.fn().mockResolvedValue({ tenants: [{ tenantId: "acme" }] }),
}));

describe("tenant-context", () => {
  let select;

  beforeEach(() => {
    sessionStorage.clear();
    document.body.innerHTML = '<select id="tc"><option value="">All</option></select>';
    select = document.querySelector("#tc");
    TenantContext.mountSelect(select);
  });

  it("getTenantId returns null initially", () => {
    expect(TenantContext.getTenantId()).toBeNull();
  });

  it("setTenantId updates the value", () => {
    TenantContext.setTenantId("acme");
    expect(TenantContext.getTenantId()).toBe("acme");
  });

  it("onChange returns unsubscribe function", () => {
    const calls = [];
    const unsub = TenantContext.onChange((tid) => calls.push(tid));
    TenantContext.setTenantId("a");
    unsub();
    TenantContext.setTenantId("b");
    expect(calls).toEqual(["a"]);
  });

  it("onChange fires on select change", () => {
    const calls = [];
    TenantContext.onChange((tid) => calls.push(tid));
    select.value = "";
    select.dispatchEvent(new Event("change"));
    expect(calls.length).toBe(1);
  });

  it("persists selected tenant to sessionStorage on change", () => {
    const opt = document.createElement("option");
    opt.value = "acme";
    opt.textContent = "acme";
    select.appendChild(opt);

    select.value = "acme";
    select.dispatchEvent(new Event("change"));

    expect(sessionStorage.getItem("docai_selected_tenant")).toBe("acme");
  });

  it("clears sessionStorage when tenant deselected", () => {
    sessionStorage.setItem("docai_selected_tenant", "acme");
    select.value = "";
    select.dispatchEvent(new Event("change"));

    expect(sessionStorage.getItem("docai_selected_tenant")).toBeNull();
  });
});

describe("tenant-context mountSelect", () => {
  it("populates select with placeholder option", () => {
    document.body.innerHTML = '<select id="tc"></select>';
    const select = document.querySelector("#tc");
    TenantContext.mountSelect(select, { placeholder: "All Tenants" });

    expect(select.options[0].textContent).toBe("All Tenants");
    expect(select.options[0].value).toBe("");
  });
});

// Regression: onChange used to fire its callback immediately on registration
// whenever a tenant was already selected. Every view calls its own load()
// unconditionally right after registering onChange, so that eager-invoke
// caused every tenant-scoped view to fetch its data twice on mount.
describe("tenant-context onChange registration", () => {
  it("does not fire immediately when registered after load() resolves with a tenant already selected", async () => {
    document.body.innerHTML = '<select id="tc-eager"></select>';
    TenantContext.mountSelect(document.querySelector("#tc-eager"));
    TenantContext.setTenantId("acme");
    await TenantContext.load();

    const calls = [];
    TenantContext.onChange((tid) => calls.push(tid));

    expect(calls).toEqual([]);
  });
});
