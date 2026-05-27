import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";

let Session;

describe("session inactivity timer", () => {
  beforeEach(async () => {
    vi.resetModules();
    vi.useFakeTimers();
    sessionStorage.clear();
    // Mock the dynamic auth import to prevent hanging
    vi.doMock("../../src/services/auth.js", () => ({
      signOut: vi.fn().mockResolvedValue(undefined),
    }));
    Session = await import("../../src/utils/session.js");
  });

  afterEach(() => {
    Session.clear();
    vi.useRealTimers();
  });

  it("fires onExpire callback after 15 minutes", async () => {
    const callback = vi.fn();
    Session.onExpire(callback);
    Session.save({
      accessToken: "at",
      idToken: "it",
      refreshToken: "rt",
      email: "a@b.com",
      expiresIn: 3600,
    });

    vi.advanceTimersByTime(15 * 60 * 1000);
    await vi.runAllTimersAsync();

    expect(callback).toHaveBeenCalledTimes(1);
  });

  it("clears session when timer fires", async () => {
    Session.onExpire(() => {});
    Session.save({
      accessToken: "at",
      idToken: "it",
      refreshToken: "rt",
      email: "a@b.com",
      expiresIn: 3600,
    });

    vi.advanceTimersByTime(15 * 60 * 1000);
    await vi.runAllTimersAsync();

    expect(Session.get()).toBeNull();
  });

  it("does not fire before 15 minutes", () => {
    const callback = vi.fn();
    Session.onExpire(callback);
    Session.save({
      accessToken: "at",
      idToken: "it",
      refreshToken: "rt",
      email: "a@b.com",
      expiresIn: 3600,
    });

    vi.advanceTimersByTime(14 * 60 * 1000);

    expect(callback).not.toHaveBeenCalled();
  });

  it("resets timer on user activity", async () => {
    const callback = vi.fn();
    Session.onExpire(callback);
    Session.save({
      accessToken: "at",
      idToken: "it",
      refreshToken: "rt",
      email: "a@b.com",
      expiresIn: 3600,
    });

    // Advance 10 minutes, then activity resets
    vi.advanceTimersByTime(10 * 60 * 1000);
    document.dispatchEvent(new Event("click"));

    // Advance 14 minutes from activity - should NOT fire (need 15)
    vi.advanceTimersByTime(14 * 60 * 1000);
    expect(callback).not.toHaveBeenCalled();

    // Advance 2 more minutes - now past 15 from last activity
    vi.advanceTimersByTime(2 * 60 * 1000);
    await vi.runAllTimersAsync();
    expect(callback).toHaveBeenCalledTimes(1);
  });

  it("does not reset timer after clear()", () => {
    const callback = vi.fn();
    Session.onExpire(callback);
    Session.save({
      accessToken: "at",
      idToken: "it",
      refreshToken: "rt",
      email: "a@b.com",
      expiresIn: 3600,
    });

    Session.clear();
    // Activity after clear should not restart timer
    document.dispatchEvent(new Event("click"));
    vi.advanceTimersByTime(15 * 60 * 1000);

    // onExpire was called once during clear's timer fire? No - clear stops the timer
    // The callback should NOT have been called since we cleared before timeout
    expect(callback).not.toHaveBeenCalled();
  });

  it("activity listeners are removed after clear()", async () => {
    const callback = vi.fn();
    Session.onExpire(callback);
    Session.save({
      accessToken: "at",
      idToken: "it",
      refreshToken: "rt",
      email: "a@b.com",
      expiresIn: 3600,
    });
    Session.clear();

    // Dispatch activity - should NOT restart timer since listeners were removed
    document.dispatchEvent(new Event("click"));
    document.dispatchEvent(new Event("keydown"));
    document.dispatchEvent(new Event("mousemove"));

    vi.advanceTimersByTime(15 * 60 * 1000);
    await vi.runAllTimersAsync();

    // Callback should never fire - no timer was restarted
    expect(callback).not.toHaveBeenCalled();
  });
});
