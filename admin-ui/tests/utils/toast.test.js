import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { show } from "../../src/utils/toast.js";

describe("toast", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("creates a toast element with message", () => {
    show("Hello");
    const toast = document.querySelector(".toast");
    expect(toast).not.toBeNull();
    expect(toast.textContent).toBe("Hello");
  });

  it("removes existing toast before showing new one", () => {
    show("First");
    show("Second");
    const toasts = document.querySelectorAll(".toast");
    expect(toasts.length).toBe(1);
    expect(toasts[0].textContent).toBe("Second");
  });

  it("removes toast after timeout", () => {
    show("Temp");
    vi.advanceTimersByTime(2800); // 2500 + 300
    expect(document.querySelector(".toast")).toBeNull();
  });
});
