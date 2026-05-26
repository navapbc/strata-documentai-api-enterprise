import { describe, it, expect, beforeEach } from "vitest";
import * as TenantContext from "../../src/utils/tenant-context.js";

describe("tenant-context", () => {
  beforeEach(() => {
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
});
