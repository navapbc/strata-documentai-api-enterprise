import { describe, it, expect, beforeEach } from "vitest";
import * as TenantContext from "../../src/utils/tenant-context.js";

describe("tenant-context", () => {
  beforeEach(() => {
    sessionStorage.clear();
    document.body.innerHTML = '<select id="tc"><option value="">All</option></select>';
    TenantContext.init(document.querySelector("#tc"));
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
    const select = document.querySelector("#tc");
    select.value = "";
    select.dispatchEvent(new Event("change"));
    expect(calls.length).toBe(1);
  });

  it("persists selected tenant to sessionStorage on change", () => {
    const select = document.querySelector("#tc");
    // Add an option to select
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
    const select = document.querySelector("#tc");
    select.value = "";
    select.dispatchEvent(new Event("change"));

    expect(sessionStorage.getItem("docai_selected_tenant")).toBeNull();
  });
});

describe("tenant-context loading state", () => {
  it("shows loading placeholder and disables select on init", () => {
    document.body.innerHTML = '<select id="tc"></select>';
    const select = document.querySelector("#tc");
    TenantContext.init(select);

    expect(select.disabled).toBe(true);
    expect(select.options[0].textContent).toBe("Loading tenants...");
  });
});
