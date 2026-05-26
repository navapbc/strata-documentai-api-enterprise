import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { buildToken } from "../factories.js";

let LoginView, Auth, mockSession, token;

const TEST_EMAIL = "user@example.com";
const TEST_PASSWORD = "TestPass123!";

function flush() {
  return new Promise((r) => setTimeout(r, 0));
}

function submitSignIn(root, email = TEST_EMAIL, password = TEST_PASSWORD) {
  root.querySelector("#sign-in-email").value = email;
  root.querySelector("#sign-in-password").value = password;
  root.querySelector("#sign-in-form").dispatchEvent(new Event("submit", { cancelable: true }));
}

function submitSignUp(
  root,
  email = TEST_EMAIL,
  password = TEST_PASSWORD,
  confirmPassword = password,
) {
  root.querySelector("#sign-up-email").value = email;
  root.querySelector("#sign-up-password").value = password;
  root.querySelector("#sign-up-password-confirm").value = confirmPassword;
  root.querySelector("#sign-up-form").dispatchEvent(new Event("submit", { cancelable: true }));
}

function submitForgot(root, email = TEST_EMAIL) {
  root.querySelector("#forgot-email").value = email;
  root
    .querySelector("#forgot-password-form")
    .dispatchEvent(new Event("submit", { cancelable: true }));
}

function submitReset(root, code, newPassword, confirmPassword = newPassword) {
  root.querySelector("#reset-code").value = code;
  root.querySelector("#reset-new-password").value = newPassword;
  root.querySelector("#reset-confirm-password").value = confirmPassword;
  root
    .querySelector("#reset-password-form")
    .dispatchEvent(new Event("submit", { cancelable: true }));
}

function submitMfa(root, code) {
  root.querySelector("#mfa-code").value = code;
  root.querySelector("#mfa-form").dispatchEvent(new Event("submit", { cancelable: true }));
}

function submitMfaSetup(root, code) {
  root.querySelector("#mfa-setup-code").value = code;
  root.querySelector("#mfa-setup-form").dispatchEvent(new Event("submit", { cancelable: true }));
}

function submitConfirm(root, code) {
  root.querySelector("#confirm-code").value = code;
  root.querySelector("#confirm-form").dispatchEvent(new Event("submit", { cancelable: true }));
}

function goToForgot(root) {
  root.querySelector("#show-forgot-password").click();
}

function goToSignUp(root) {
  root.querySelector("#show-sign-up").click();
}

async function goToReset(root) {
  goToForgot(root);
  submitForgot(root);
  await flush();
}

describe("login view", () => {
  let root;

  beforeEach(async () => {
    vi.resetModules();
    token = buildToken();

    Auth = {
      signIn: vi.fn(),
      signUp: vi.fn().mockResolvedValue({}),
      confirmSignUp: vi.fn().mockResolvedValue({}),
      signOut: vi.fn(),
      associateSoftwareToken: vi
        .fn()
        .mockResolvedValue({ Session: "new-sess", SecretCode: "JBSWY3DPEHPK3PXP" }),
      respondToMfaChallenge: vi.fn().mockResolvedValue(token),
      verifySoftwareToken: vi.fn().mockResolvedValue(token),
      forgotPassword: vi.fn().mockResolvedValue({}),
      confirmForgotPassword: vi.fn().mockResolvedValue({}),
      configure: vi.fn(),
    };
    vi.doMock("../../src/services/auth.js", () => Auth);

    mockSession = { save: vi.fn(), clear: vi.fn(), get: vi.fn() };
    vi.doMock("../../src/utils/session.js", () => mockSession);
    vi.doMock("qrcode", () => ({ default: { toCanvas: vi.fn().mockResolvedValue(undefined) } }));

    LoginView = await import("../../src/views/login/login.js");
    root = document.createElement("div");
    document.body.appendChild(root);
  });

  afterEach(() => {
    document.body.innerHTML = "";
  });

  // --- Sign In ---

  it("successful sign-in saves session and calls onLogin", async () => {
    Auth.signIn.mockResolvedValue(token);
    const onLogin = vi.fn();
    LoginView.onLoginSuccess(onLogin);
    LoginView.mount(root);

    submitSignIn(root);
    await flush();

    expect(mockSession.save).toHaveBeenCalledWith(
      expect.objectContaining({ email: TEST_EMAIL, accessToken: token.accessToken }),
    );
    expect(onLogin).toHaveBeenCalled();
  });

  it("shows MFA card on SOFTWARE_TOKEN_MFA challenge", async () => {
    Auth.signIn.mockResolvedValue({ challenge: "SOFTWARE_TOKEN_MFA", session: "sess" });
    LoginView.mount(root);

    submitSignIn(root);
    await flush();

    expect(root.querySelector("#mfa-card").classList.contains("hidden")).toBe(false);
    expect(root.querySelector("#sign-in-card").classList.contains("hidden")).toBe(true);
  });

  it("shows MFA setup card on MFA_SETUP challenge", async () => {
    Auth.signIn.mockResolvedValue({ challenge: "MFA_SETUP", session: "setup-sess" });
    LoginView.mount(root);

    submitSignIn(root);
    await flush();

    expect(root.querySelector("#mfa-setup-card").classList.contains("hidden")).toBe(false);
    expect(Auth.associateSoftwareToken).toHaveBeenCalledWith("setup-sess");
    expect(root.querySelector("#mfa-secret-code").textContent).toBe("JBSWY3DPEHPK3PXP");
  });

  it("shows error on NotAuthorizedException", async () => {
    Auth.signIn.mockRejectedValue({ code: "NotAuthorizedException", message: "bad" });
    LoginView.mount(root);

    submitSignIn(root);
    await flush();

    const error = root.querySelector("#sign-in-error");
    expect(error.classList.contains("hidden")).toBe(false);
    expect(error.textContent).toBe("Incorrect email or password");
  });

  it("shows error on UserNotFoundException", async () => {
    Auth.signIn.mockRejectedValue({ code: "UserNotFoundException", message: "no" });
    LoginView.mount(root);

    submitSignIn(root, "ghost@co.com");
    await flush();

    expect(root.querySelector("#sign-in-error").textContent).toBe("Incorrect email or password");
  });

  it("shows error on ResourceNotFoundException", async () => {
    Auth.signIn.mockRejectedValue({ code: "ResourceNotFoundException", message: "no pool" });
    LoginView.mount(root);

    submitSignIn(root);
    await flush();

    expect(root.querySelector("#sign-in-error").textContent).toContain("Service not configured");
  });

  // --- MFA Verify ---

  it("MFA verify submits code and saves session", async () => {
    Auth.signIn.mockResolvedValue({ challenge: "SOFTWARE_TOKEN_MFA", session: "mfa-sess" });
    const onLogin = vi.fn();
    LoginView.onLoginSuccess(onLogin);
    LoginView.mount(root);

    submitSignIn(root);
    await flush();

    submitMfa(root, "123456");
    await flush();

    expect(Auth.respondToMfaChallenge).toHaveBeenCalledWith("mfa-sess", "123456", TEST_EMAIL);
    expect(mockSession.save).toHaveBeenCalled();
    expect(onLogin).toHaveBeenCalled();
  });

  it("MFA verify shows error on CodeMismatchException", async () => {
    Auth.signIn.mockResolvedValue({ challenge: "SOFTWARE_TOKEN_MFA", session: "s" });
    Auth.respondToMfaChallenge.mockRejectedValue({ code: "CodeMismatchException", message: "bad" });
    LoginView.mount(root);

    submitSignIn(root);
    await flush();

    submitMfa(root, "000000");
    await flush();

    expect(root.querySelector("#mfa-error").textContent).toBe("Invalid code. Please try again.");
  });

  // --- MFA Setup Verify ---

  it("MFA setup verify submits code and saves session", async () => {
    Auth.signIn.mockResolvedValue({ challenge: "MFA_SETUP", session: "setup-sess" });
    const onLogin = vi.fn();
    LoginView.onLoginSuccess(onLogin);
    LoginView.mount(root);

    submitSignIn(root);
    await flush();

    submitMfaSetup(root, "654321");
    await flush();

    expect(Auth.verifySoftwareToken).toHaveBeenCalledWith("new-sess", "654321", TEST_EMAIL);
    expect(mockSession.save).toHaveBeenCalled();
    expect(onLogin).toHaveBeenCalled();
  });

  it("MFA setup cancel resets to sign-in", () => {
    LoginView.mount(root);

    root.querySelector("#mfa-setup-card").classList.remove("hidden");
    root.querySelector("#sign-in-card").classList.add("hidden");
    root.querySelector("#mfa-setup-cancel").click();

    expect(root.querySelector("#sign-in-card").classList.contains("hidden")).toBe(false);
    expect(root.querySelector("#mfa-setup-card").classList.contains("hidden")).toBe(true);
  });

  // --- Sign Up ---

  it("sign-up submits and shows confirm card", async () => {
    LoginView.mount(root);
    goToSignUp(root);

    submitSignUp(root);
    await flush();

    expect(Auth.signUp).toHaveBeenCalledWith(TEST_EMAIL, TEST_PASSWORD);
    expect(root.querySelector("#confirm-card").classList.contains("hidden")).toBe(false);
    expect(root.querySelector("#confirm-email-display").textContent).toBe(TEST_EMAIL);
  });

  it("sign-up shows error on password mismatch", async () => {
    LoginView.mount(root);
    goToSignUp(root);

    submitSignUp(root, TEST_EMAIL, "Pass1", "Pass2");
    await flush();

    expect(Auth.signUp).not.toHaveBeenCalled();
    const error = root.querySelector("#sign-up-error");
    expect(error.classList.contains("hidden")).toBe(false);
    expect(error.textContent).toBe("Passwords do not match");
  });

  it("sign-up shows error on InvalidPasswordException", async () => {
    Auth.signUp.mockRejectedValue({ code: "InvalidPasswordException", message: "too short" });
    LoginView.mount(root);
    goToSignUp(root);

    submitSignUp(root, TEST_EMAIL, "short");
    await flush();

    expect(root.querySelector("#sign-up-error").textContent).toBe(
      "Password must be at least 12 characters",
    );
  });

  // --- Confirm Sign Up ---

  it("confirm submits code and signs in", async () => {
    Auth.signIn.mockResolvedValue(token);
    const onLogin = vi.fn();
    LoginView.onLoginSuccess(onLogin);
    LoginView.mount(root);

    goToSignUp(root);
    submitSignUp(root);
    await flush();

    submitConfirm(root, "123456");
    await flush();

    expect(Auth.confirmSignUp).toHaveBeenCalledWith(TEST_EMAIL, "123456");
    expect(Auth.signIn).toHaveBeenCalledWith(TEST_EMAIL, TEST_PASSWORD);
    expect(onLogin).toHaveBeenCalled();
  });

  it("confirm shows error on bad code", async () => {
    Auth.confirmSignUp.mockRejectedValue({ code: "CodeMismatchException", message: "bad" });
    LoginView.mount(root);

    goToSignUp(root);
    submitSignUp(root);
    await flush();

    submitConfirm(root, "000000");
    await flush();

    expect(root.querySelector("#confirm-error").classList.contains("hidden")).toBe(false);
  });

  // --- UI toggles ---

  it("show-sign-up toggles cards", () => {
    LoginView.mount(root);
    goToSignUp(root);
    expect(root.querySelector("#sign-in-card").classList.contains("hidden")).toBe(true);
    expect(root.querySelector("#sign-up-card").classList.contains("hidden")).toBe(false);
  });

  it("show-sign-in toggles back", () => {
    LoginView.mount(root);
    goToSignUp(root);
    root.querySelector("#show-sign-in").click();
    expect(root.querySelector("#sign-in-card").classList.contains("hidden")).toBe(false);
    expect(root.querySelector("#sign-up-card").classList.contains("hidden")).toBe(true);
  });

  it("show-password toggles input type", () => {
    LoginView.mount(root);
    const btn = root.querySelector(".show-password");
    const input = root.querySelector("#sign-in-password");

    btn.click();
    expect(input.type).toBe("text");
    expect(btn.textContent).toBe("Hide password");

    btn.click();
    expect(input.type).toBe("password");
    expect(btn.textContent).toBe("Show password");
  });

  it("unmount clears root", () => {
    LoginView.mount(root);
    LoginView.unmount(root);
    expect(root.children.length).toBe(0);
  });

  // --- Forgot Password ---

  it("forgot-password link shows forgot card", () => {
    LoginView.mount(root);
    goToForgot(root);
    expect(root.querySelector("#sign-in-card").classList.contains("hidden")).toBe(true);
    expect(root.querySelector("#forgot-password-card").classList.contains("hidden")).toBe(false);
  });

  it("forgot-password back link returns to sign-in", () => {
    LoginView.mount(root);
    goToForgot(root);
    root.querySelector("#forgot-back-to-sign-in").click();
    expect(root.querySelector("#forgot-password-card").classList.contains("hidden")).toBe(true);
    expect(root.querySelector("#sign-in-card").classList.contains("hidden")).toBe(false);
  });

  it("forgot-password submit sends code and shows reset card", async () => {
    LoginView.mount(root);
    await goToReset(root);

    expect(Auth.forgotPassword).toHaveBeenCalledWith(TEST_EMAIL);
    expect(root.querySelector("#forgot-password-card").classList.contains("hidden")).toBe(true);
    expect(root.querySelector("#reset-password-card").classList.contains("hidden")).toBe(false);
  });

  it("forgot-password shows error on empty email", async () => {
    LoginView.mount(root);
    goToForgot(root);

    submitForgot(root, "");
    await flush();

    expect(Auth.forgotPassword).not.toHaveBeenCalled();
    const error = root.querySelector("#forgot-password-error");
    expect(error.classList.contains("hidden")).toBe(false);
    expect(error.textContent).toBe("Email is required");
  });

  it("forgot-password hides user-not-found (no user enumeration)", async () => {
    Auth.forgotPassword.mockRejectedValue({ code: "UserNotFoundException", message: "no" });
    LoginView.mount(root);
    await goToReset(root);

    expect(root.querySelector("#reset-password-card").classList.contains("hidden")).toBe(false);
  });

  it("forgot-password shows rate limit error", async () => {
    Auth.forgotPassword.mockRejectedValue({ code: "LimitExceededException", message: "too many" });
    LoginView.mount(root);
    goToForgot(root);

    submitForgot(root);
    await flush();

    const error = root.querySelector("#forgot-password-error");
    expect(error.classList.contains("hidden")).toBe(false);
    expect(error.textContent).toContain("Too many attempts");
  });

  // --- Reset Password ---

  it("reset-password submits code + new password and signs in", async () => {
    Auth.signIn.mockResolvedValue(token);
    const onLogin = vi.fn();
    LoginView.onLoginSuccess(onLogin);
    LoginView.mount(root);

    await goToReset(root);

    const newPassword = "NewStrongPass1!";
    submitReset(root, "123456", newPassword);
    await flush();

    expect(Auth.confirmForgotPassword).toHaveBeenCalledWith(TEST_EMAIL, "123456", newPassword);
    expect(Auth.signIn).toHaveBeenCalledWith(TEST_EMAIL, newPassword);
    expect(onLogin).toHaveBeenCalled();
  });

  it("reset-password shows error on password mismatch", async () => {
    LoginView.mount(root);
    await goToReset(root);

    submitReset(root, "123456", "Pass1", "Pass2");
    await flush();

    expect(Auth.confirmForgotPassword).not.toHaveBeenCalled();
    const error = root.querySelector("#reset-password-error");
    expect(error.classList.contains("hidden")).toBe(false);
    expect(error.textContent).toBe("Passwords do not match");
  });

  it("reset-password shows error on expired code", async () => {
    Auth.confirmForgotPassword.mockRejectedValue({
      code: "ExpiredCodeException",
      message: "expired",
    });
    LoginView.mount(root);
    await goToReset(root);

    submitReset(root, "000000", TEST_PASSWORD);
    await flush();

    const error = root.querySelector("#reset-password-error");
    expect(error.classList.contains("hidden")).toBe(false);
    expect(error.textContent).toContain("Invalid or expired code");
  });
});
