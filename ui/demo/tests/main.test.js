import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock fetch globally
global.fetch = vi.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve({}) }));

// Mock QRCode
vi.mock("qrcode", () => ({ default: { toCanvas: vi.fn() } }));

describe("demo main", () => {
  beforeEach(() => {
    document.body.innerHTML = '<div id="app"></div>';
    sessionStorage.clear();
  });

  it("shows login when no session exists", async () => {
    await import("../src/main.js");
    // Should render login form
    const app = document.getElementById("app");
    expect(app.querySelector("#sign-in-form")).toBeTruthy();
  });
});
