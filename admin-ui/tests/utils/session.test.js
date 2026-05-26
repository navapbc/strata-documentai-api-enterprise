import { describe, it, expect, beforeEach } from "vitest";
import * as Session from "../../src/utils/session.js";

describe("session", () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  it("get returns null when no session", () => {
    expect(Session.get()).toBeNull();
  });

  it("save stores session and get retrieves it", () => {
    Session.save({
      accessToken: "at",
      idToken: "it",
      refreshToken: "rt",
      email: "test@example.com",
      expiresIn: 3600,
    });
    const session = Session.get();
    expect(session.accessToken).toBe("at");
    expect(session.email).toBe("test@example.com");
    expect(session.expiresAt).toBeGreaterThan(Date.now());
  });

  it("clear removes session", () => {
    Session.save({
      accessToken: "at",
      idToken: "it",
      refreshToken: "rt",
      email: "test@example.com",
      expiresIn: 3600,
    });
    Session.clear();
    expect(Session.get()).toBeNull();
  });

  it("isExpired returns true when no session", () => {
    expect(Session.isExpired()).toBe(true);
  });

  it("isExpired returns false for valid session", () => {
    Session.save({
      accessToken: "at",
      idToken: "it",
      refreshToken: "rt",
      email: "test@example.com",
      expiresIn: 3600,
    });
    expect(Session.isExpired()).toBe(false);
  });

  it("isExpired returns true for expired session", () => {
    Session.save({
      accessToken: "at",
      idToken: "it",
      refreshToken: "rt",
      email: "test@example.com",
      expiresIn: -1,
    });
    expect(Session.isExpired()).toBe(true);
  });

  it("getRoles returns empty array when no session", () => {
    expect(Session.getRoles()).toEqual([]);
  });

  it("getRoles decodes groups from idToken", () => {
    // Create a fake JWT with cognito:groups
    const payload = btoa(JSON.stringify({ "cognito:groups": ["super-admin"], email: "a@b.com" }));
    const fakeToken = `header.${payload}.sig`;
    Session.save({
      accessToken: "at",
      idToken: fakeToken,
      refreshToken: "rt",
      email: "a@b.com",
      expiresIn: 3600,
    });
    expect(Session.getRoles()).toEqual(["super-admin"]);
  });

  it("isSuperAdmin returns true for super-admin role", () => {
    const payload = btoa(JSON.stringify({ "cognito:groups": ["super-admin"] }));
    const fakeToken = `h.${payload}.s`;
    Session.save({
      accessToken: "at",
      idToken: fakeToken,
      refreshToken: "rt",
      email: "a@b.com",
      expiresIn: 3600,
    });
    expect(Session.isSuperAdmin()).toBe(true);
  });

  it("isSuperAdmin returns false for tenant-admin", () => {
    const payload = btoa(JSON.stringify({ "cognito:groups": ["tenant-admin"] }));
    const fakeToken = `h.${payload}.s`;
    Session.save({
      accessToken: "at",
      idToken: fakeToken,
      refreshToken: "rt",
      email: "a@b.com",
      expiresIn: 3600,
    });
    expect(Session.isSuperAdmin()).toBe(false);
  });

  it("isApproved returns true for any role", () => {
    const payload = btoa(JSON.stringify({ "cognito:groups": ["tenant-admin"] }));
    const fakeToken = `h.${payload}.s`;
    Session.save({
      accessToken: "at",
      idToken: fakeToken,
      refreshToken: "rt",
      email: "a@b.com",
      expiresIn: 3600,
    });
    expect(Session.isApproved()).toBe(true);
  });

  it("isApproved returns false with no groups", () => {
    const payload = btoa(JSON.stringify({ email: "a@b.com" }));
    const fakeToken = `h.${payload}.s`;
    Session.save({
      accessToken: "at",
      idToken: fakeToken,
      refreshToken: "rt",
      email: "a@b.com",
      expiresIn: 3600,
    });
    expect(Session.isApproved()).toBe(false);
  });
});

describe("update()", () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  it("returns null if no session exists", () => {
    expect(Session.update({ accessToken: "x", idToken: "y", expiresIn: 60 })).toBeNull();
  });

  it("updates tokens without changing email or refreshToken", () => {
    Session.save({
      accessToken: "old-at",
      idToken: "old-it",
      refreshToken: "rt",
      email: "a@b.com",
      expiresIn: 3600,
    });

    Session.update({ accessToken: "new-at", idToken: "new-it", expiresIn: 7200 });

    const session = Session.get();
    expect(session.accessToken).toBe("new-at");
    expect(session.idToken).toBe("new-it");
    expect(session.refreshToken).toBe("rt");
    expect(session.email).toBe("a@b.com");
  });
});

describe("getAccessToken()", () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  it("returns null when no session", () => {
    expect(Session.getAccessToken()).toBeNull();
  });

  it("returns token from session", () => {
    Session.save({
      accessToken: "my-token",
      idToken: "it",
      refreshToken: "rt",
      email: "a@b.com",
      expiresIn: 3600,
    });
    expect(Session.getAccessToken()).toBe("my-token");
  });
});
