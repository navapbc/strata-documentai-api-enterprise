import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { buildAuditEvent } from "../factories.js";

let AuditLogView, mockList, mockListActions, mockListActors;

function flush() {
  return new Promise((r) => setTimeout(r, 0));
}

describe("audit-log view", () => {
  let root;

  beforeEach(async () => {
    vi.resetModules();

    mockList = vi.fn().mockResolvedValue({ events: [], nextCursor: null });
    mockListActions = vi.fn().mockResolvedValue({ actions: ["key.create", "key.revoke"] });
    mockListActors = vi.fn().mockResolvedValue({ actors: [] });

    vi.doMock("../../src/services/audit-log.js", () => ({
      list: mockList,
      listActions: mockListActions,
      listActors: mockListActors,
    }));
    vi.doMock("../../src/utils/tenant-context.js", () => ({
      getTenantId: vi.fn(() => "acme"),
      onChange: vi.fn(() => () => {}),
    }));
    vi.doMock("../../src/utils/helpers.js", () => ({
      esc: (s) => s,
      formatDate: (d) => d || "-",
      formatDateTime: (d) => d || "-",
      showLoading: vi.fn(),
      setViewActions: vi.fn(),
      clearViewActions: vi.fn(),
      bindSortHeaders: vi.fn(() => () => {}),
      sortRows: (rows) => rows,
      localDateToUtcStart: (d) => new Date(d + "T00:00:00").toISOString(),
      localDateToUtcEnd: (d) => new Date(d + "T23:59:59.999").toISOString(),
    }));

    AuditLogView = await import("../../src/views/audit-log/audit-log.js");
    root = document.createElement("div");
    document.body.appendChild(root);
  });

  afterEach(() => {
    document.body.innerHTML = "";
  });

  it("mounts and loads events + actions", async () => {
    AuditLogView.mount(root);
    await flush();
    expect(mockList).toHaveBeenCalled();
    expect(mockListActions).toHaveBeenCalled();
  });

  it("renders event rows", async () => {
    mockList.mockResolvedValue({
      events: [buildAuditEvent()],
      nextCursor: null,
    });
    AuditLogView.mount(root);
    await flush();
    expect(root.querySelectorAll("#audit-tbody tr").length).toBe(2);
  });

  it("shows empty state when no events", async () => {
    AuditLogView.mount(root);
    await flush();
    expect(root.querySelector("#no-audit-events").classList.contains("hidden")).toBe(false);
  });

  // --- Pagination ---

  it("next button enabled when nextCursor present", async () => {
    const events = Array.from({ length: 50 }, () => buildAuditEvent());
    mockList.mockResolvedValue({
      events,
      nextCursor: "cur1",
    });
    AuditLogView.mount(root);
    await flush();
    expect(root.querySelector("#audit-next-btn").disabled).toBe(false);
  });

  it("clicking next loads next page", async () => {
    const events = Array.from({ length: 50 }, () => buildAuditEvent());
    mockList.mockResolvedValue({
      events,
      nextCursor: "page2",
    });
    AuditLogView.mount(root);
    await flush();

    mockList.mockResolvedValue({ events: [], nextCursor: null });
    root.querySelector("#audit-next-btn").click();
    await flush();

    const lastCall = mockList.mock.calls[mockList.mock.calls.length - 1][0];
    expect(lastCall.cursor).toBe("page2");
  });

  it("clicking prev goes back to previous page", async () => {
    mockList.mockResolvedValue({
      events: [buildAuditEvent()],
      nextCursor: "page2",
    });
    AuditLogView.mount(root);
    await flush();

    mockList.mockResolvedValue({ events: [], nextCursor: null });
    root.querySelector("#audit-next-btn").click();
    await flush();

    root.querySelector("#audit-prev-btn").click();
    await flush();

    const lastCall = mockList.mock.calls[mockList.mock.calls.length - 1][0];
    expect(lastCall.cursor).toBeUndefined();
  });

  it("prev button disabled on first page", async () => {
    AuditLogView.mount(root);
    await flush();
    expect(root.querySelector("#audit-prev-btn").disabled).toBe(true);
  });

  it("unmount clears root", () => {
    AuditLogView.mount(root);
    AuditLogView.unmount(root);
    expect(root.children.length).toBe(0);
  });

  // --- Date range ---

  it("preset sends full UTC ISO timestamps to audit service", async () => {
    AuditLogView.mount(root);
    await flush();
    const call = mockList.mock.calls[0][0];
    expect(call.startDate).toMatch(/^\d{4}-\d{2}-\d{2}T/);
    expect(call.endDate).toMatch(/^\d{4}-\d{2}-\d{2}T/);
  });

  it("custom range end date includes full last second (T23:59:59.999)", async () => {
    AuditLogView.mount(root);
    await flush();
    const startInput = root.querySelector("#audit-start-date");
    const endInput = root.querySelector("#audit-end-date");
    const loadBtn = root.querySelector("#audit-load-btn");
    root.querySelector("#audit-timeframe").value = "custom";
    root.querySelector("#audit-timeframe").dispatchEvent(new Event("change"));
    startInput.value = "2026-08-05";
    endInput.value = "2026-08-06";
    loadBtn.click();
    await flush();
    const call = mockList.mock.calls[mockList.mock.calls.length - 1][0];
    expect(call.endDate).toMatch(/\.999Z$/);
    expect(call.startDate).toMatch(/T\d{2}:00:00\.000Z$/);
  });
});
