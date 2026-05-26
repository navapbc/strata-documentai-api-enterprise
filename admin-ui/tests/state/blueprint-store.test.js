import { describe, it, expect, beforeEach } from "vitest";
import * as Store from "../../src/state/blueprint-store.js";

describe("blueprint-store", () => {
  beforeEach(() => {
    Store.reset();
  });

  it("starts with empty state", () => {
    const state = Store.get();
    expect(state.schemas).toEqual({});
    expect(state.activeDocType).toBeNull();
    expect(state.rules).toEqual({});
    expect(state.dirty).toBe(false);
    expect(state.tenantId).toBeNull();
    expect(state.schemasLoading).toBe(true);
  });

  it("set merges state", () => {
    Store.set({ activeDocType: "W2", dirty: true });
    const state = Store.get();
    expect(state.activeDocType).toBe("W2");
    expect(state.dirty).toBe(true);
    expect(state.schemas).toEqual({});
  });

  it("subscribe notifies on set", () => {
    const calls = [];
    Store.subscribe((state) => calls.push(state.activeDocType));
    Store.set({ activeDocType: "Payslip" });
    Store.set({ activeDocType: "W2" });
    expect(calls).toEqual(["Payslip", "W2"]);
  });

  it("subscribe returns unsubscribe function", () => {
    const calls = [];
    const unsub = Store.subscribe((state) => calls.push(state.activeDocType));
    Store.set({ activeDocType: "A" });
    unsub();
    Store.set({ activeDocType: "B" });
    expect(calls).toEqual(["A"]);
  });

  it("reset restores initial state", () => {
    Store.set({ activeDocType: "W2", dirty: true, schemasLoading: false });
    Store.reset();
    const state = Store.get();
    expect(state.activeDocType).toBeNull();
    expect(state.dirty).toBe(false);
    expect(state.schemasLoading).toBe(true);
  });
});
