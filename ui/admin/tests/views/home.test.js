import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import NAV_SECTIONS from "../../src/config/nav.js";

let HomeView, Session;

describe("home view", () => {
  let root;

  beforeEach(async () => {
    vi.resetModules();

    vi.doMock("../../src/utils/session.js", () => ({
      get: vi.fn(() => ({ email: "admin@test.com" })),
      isSuperAdmin: vi.fn(() => false),
    }));

    HomeView = await import("../../src/views/home/home.js");
    Session = await import("../../src/utils/session.js");
    root = document.createElement("div");
    document.body.appendChild(root);
  });

  afterEach(() => {
    document.body.innerHTML = "";
  });

  it("renders the user's email in the welcome message", () => {
    HomeView.mount(root);
    expect(root.querySelector("#home-email").textContent).toBe("admin@test.com");
  });

  it("renders a card linking to each page section", () => {
    HomeView.mount(root);
    expect(root.querySelector('a[href="#documents"]')).toBeTruthy();
    expect(root.querySelector('a[href="#keys"]')).toBeTruthy();
    expect(root.querySelector('a[href="#metrics"]')).toBeTruthy();
    expect(root.querySelector('a[href="#blueprints"]')).toBeTruthy();
  });

  it("renders a card for each nav section", () => {
    HomeView.mount(root);
    expect(root.querySelectorAll(".home-card").length).toBe(NAV_SECTIONS.length);
  });

  it("injects an icon into each home card", () => {
    HomeView.mount(root);
    root.querySelectorAll(".home-card-icon").forEach((el) => {
      expect(el.querySelector("svg")).toBeTruthy();
    });
  });

  it("hides super-admin-only links for non-super-admins", () => {
    Session.isSuperAdmin.mockReturnValue(false);
    HomeView.mount(root);
    expect(root.querySelector('a[href="#users"]').classList.contains("hidden")).toBe(true);
    expect(root.querySelector('a[href="#tenants"]').classList.contains("hidden")).toBe(true);
  });

  it("shows super-admin-only links for super-admins", () => {
    Session.isSuperAdmin.mockReturnValue(true);
    HomeView.mount(root);
    expect(root.querySelector('a[href="#users"]').classList.contains("hidden")).toBe(false);
    expect(root.querySelector('a[href="#tenants"]').classList.contains("hidden")).toBe(false);
  });

  it("unmount clears the root", () => {
    HomeView.mount(root);
    HomeView.unmount(root);
    expect(root.children.length).toBe(0);
  });
});
