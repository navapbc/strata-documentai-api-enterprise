import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock QRCode
vi.mock("qrcode", () => ({ default: { toCanvas: vi.fn() } }));

// Mock shared auth
vi.mock("../../../../shared/services/auth.js", () => ({
  COGNITO_REGION: "us-east-1",
  configure: vi.fn(),
  signIn: vi.fn(),
  signUp: vi.fn(),
  confirmSignUp: vi.fn(),
  respondToMfaChallenge: vi.fn(),
  associateSoftwareToken: vi.fn(),
  verifySoftwareToken: vi.fn(),
  signOut: vi.fn(),
  forgotPassword: vi.fn(),
  confirmForgotPassword: vi.fn(),
  exchangeCodeForTokens: vi.fn(),
}));

let LoginView;

describe("demo login - Google SSO", () => {
  beforeEach(async () => {
    vi.resetModules();
    document.body.innerHTML = '<div id="app"></div>';
    LoginView = await import("../src/views/login/login.js");
  });

  it("hides Google SSO button when not configured", () => {
    const root = document.getElementById("app");
    LoginView.mount(root, {});

    const btn = root.querySelector("#google-sso-btn");
    expect(btn.classList.contains("hidden")).toBe(true);
  });

  it("shows Google SSO button when googleEnabled and cognitoDomain set", () => {
    const root = document.getElementById("app");
    LoginView.mount(root, {
      googleEnabled: true,
      cognitoDomain: "my-domain",
      cognitoClientId: "client123",
      redirectUri: "http://localhost:3000/callback",
    });

    const btn = root.querySelector("#google-sso-btn");
    expect(btn.classList.contains("hidden")).toBe(false);

    const divider = root.querySelector("#login-divider");
    expect(divider.classList.contains("hidden")).toBe(false);
  });

  it("redirects to Cognito authorize endpoint on Google button click", async () => {
    // Mock crypto APIs
    const mockUUID = "test-state-uuid";
    vi.stubGlobal("crypto", {
      randomUUID: () => mockUUID,
      getRandomValues: (arr) => {
        for (let i = 0; i < arr.length; i++) arr[i] = i;
        return arr;
      },
      subtle: {
        digest: async (_, data) => new Uint8Array(data).buffer,
      },
    });

    delete window.location;
    window.location = { href: "", origin: "http://localhost:3000" };

    const root = document.getElementById("app");
    LoginView.mount(root, {
      googleEnabled: true,
      cognitoDomain: "my-domain",
      cognitoClientId: "client123",
      redirectUri: "http://localhost:3000/callback",
    });

    const btn = root.querySelector("#google-sso-btn");
    btn.click();

    // Allow microtask (generateCodeChallenge is async)
    await new Promise((r) => setTimeout(r, 0));

    expect(window.location.href).toContain(
      "https://my-domain.auth.us-east-1.amazoncognito.com/oauth2/authorize",
    );
    expect(window.location.href).toContain("identity_provider=Google");
    expect(window.location.href).toContain("client_id=client123");
    expect(window.location.href).toContain(`state=${mockUUID}`);
    expect(window.location.href).toContain("code_challenge_method=S256");

    // Verify PKCE verifier was stored
    expect(sessionStorage.getItem("oauth_code_verifier")).toBeTruthy();
    expect(sessionStorage.getItem("oauth_state")).toBe(mockUUID);

    vi.unstubAllGlobals();
  });
});
