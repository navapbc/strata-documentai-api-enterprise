import * as Auth from "../../../../shared/services/auth.js";
import { COGNITO_REGION } from "../../../../shared/services/auth.js";
import * as Session from "../../../../shared/utils/session.js";
import QRCode from "qrcode";
import { tpl } from "../../../../shared/utils/tpl.js";
import html from "./login.html";

const tmpl = tpl(html);

let _onLogin = null;
let _pendingEmail = null;
let _mfaSession = null;
let _root = null;
let _ssoConfig = null;

export function onLoginSuccess(callback) {
  _onLogin = callback;
}

export function mount(root, ssoConfig = {}) {
  _root = root;
  _ssoConfig = ssoConfig;
  root.replaceChildren(tmpl());

  // Show Google SSO button if configured
  if (_ssoConfig.googleEnabled && _ssoConfig.cognitoDomain) {
    const ssoBtn = root.querySelector("#google-sso-btn");
    const divider = root.querySelector("#login-divider");
    if (ssoBtn) {
      ssoBtn.classList.remove("hidden");
      ssoBtn.addEventListener("click", handleGoogleSignIn);
    }
    if (divider) divider.classList.remove("hidden");
  }

  root.querySelector("#sign-in-form").addEventListener("submit", handleSignIn);
  root.querySelector("#sign-up-form").addEventListener("submit", handleSignUp);
  root.querySelector("#confirm-form").addEventListener("submit", handleConfirm);
  root.querySelector("#mfa-form").addEventListener("submit", handleMfaVerify);
  root.querySelector("#mfa-setup-form").addEventListener("submit", handleMfaSetupVerify);
  root.querySelector("#mfa-setup-cancel").addEventListener("click", () => reset());

  root.querySelector("#show-sign-up").addEventListener("click", (e) => {
    e.preventDefault();
    root.querySelector("#sign-in-card").classList.add("hidden");
    root.querySelector("#sign-up-card").classList.remove("hidden");
  });

  root.querySelector("#show-sign-in").addEventListener("click", (e) => {
    e.preventDefault();
    hideAll();
    root.querySelector("#sign-in-card").classList.remove("hidden");
  });

  root.querySelector("#show-forgot-password").addEventListener("click", (e) => {
    e.preventDefault();
    root.querySelector("#sign-in-card").classList.add("hidden");
    root.querySelector("#forgot-password-card").classList.remove("hidden");
  });

  root.querySelector("#forgot-back-to-sign-in").addEventListener("click", (e) => {
    e.preventDefault();
    root.querySelector("#forgot-password-card").classList.add("hidden");
    root.querySelector("#sign-in-card").classList.remove("hidden");
  });

  root.querySelector("#forgot-password-form").addEventListener("submit", handleForgotPassword);
  root.querySelector("#reset-password-form").addEventListener("submit", handleResetPassword);

  root.querySelectorAll(".show-password").forEach((btn) => {
    btn.addEventListener("click", () => {
      const input = root.querySelector(`#${btn.dataset.target}`);
      if (!input) return;
      const showing = input.type === "text";
      input.type = showing ? "password" : "text";
      btn.textContent = showing ? "Show password" : "Hide password";
    });
  });
}

export function unmount(root) {
  root.replaceChildren();
  _pendingEmail = null;
  _mfaSession = null;
}

async function handleGoogleSignIn() {
  const { cognitoDomain, cognitoClientId, redirectUri } = _ssoConfig;

  // PKCE: generate code_verifier and code_challenge
  const verifier = generateCodeVerifier();
  const challenge = await generateCodeChallenge(verifier);

  // CSRF: generate state
  const state = crypto.randomUUID();

  // Persist for callback validation
  sessionStorage.setItem("oauth_code_verifier", verifier);
  sessionStorage.setItem("oauth_state", state);

  const url =
    `https://${cognitoDomain}.auth.${COGNITO_REGION}.amazoncognito.com/oauth2/authorize?` +
    new URLSearchParams({
      identity_provider: "Google",
      response_type: "code",
      client_id: cognitoClientId,
      redirect_uri: redirectUri,
      scope: "openid email profile",
      code_challenge: challenge,
      code_challenge_method: "S256",
      state,
    });
  window.location.href = url;
}

function generateCodeVerifier() {
  const array = new Uint8Array(32);
  crypto.getRandomValues(array);
  return btoa(String.fromCharCode(...array))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
}

async function generateCodeChallenge(verifier) {
  const encoded = new TextEncoder().encode(verifier);
  const hash = await crypto.subtle.digest("SHA-256", encoded);
  return btoa(String.fromCharCode(...new Uint8Array(hash)))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
}

function hideAll() {
  if (!_root) return;
  const cards = [
    "#sign-in-card",
    "#sign-up-card",
    "#confirm-card",
    "#mfa-card",
    "#mfa-setup-card",
    "#forgot-password-card",
    "#reset-password-card",
  ];
  cards.forEach((id) => _root.querySelector(id)?.classList.add("hidden"));
}

function reset() {
  hideAll();
  _root.querySelector("#sign-in-card").classList.remove("hidden");
  _pendingEmail = null;
  _mfaSession = null;
}

async function handleSignIn(e) {
  e.preventDefault();
  const error = _root.querySelector("#sign-in-error");
  error.classList.add("hidden");

  const email = _root.querySelector("#sign-in-email").value.trim();
  const password = _root.querySelector("#sign-in-password").value;

  try {
    const result = await Auth.signIn(email, password);

    if (result.challenge === "SOFTWARE_TOKEN_MFA") {
      _pendingEmail = email;
      _mfaSession = result.session;
      hideAll();
      _root.querySelector("#mfa-card").classList.remove("hidden");
      return;
    }

    if (result.challenge === "MFA_SETUP") {
      _pendingEmail = email;
      _mfaSession = result.session;
      await showMfaSetupCard(result.session);
      return;
    }

    Session.save({ ...result, email });
    if (_onLogin) _onLogin();
  } catch (err) {
    if (err.code === "NotAuthorizedException" || err.code === "UserNotFoundException") {
      error.textContent = "Incorrect email or password";
    } else if (err.code === "UserNotConfirmedException") {
      error.textContent = "Please confirm your email first";
    } else {
      error.textContent = err.message;
    }
    error.classList.remove("hidden");
  }
}

async function handleSignUp(e) {
  e.preventDefault();
  const error = _root.querySelector("#sign-up-error");
  error.classList.add("hidden");

  const email = _root.querySelector("#sign-up-email").value.trim();
  const password = _root.querySelector("#sign-up-password").value;
  const confirmPassword = _root.querySelector("#sign-up-password-confirm").value;

  if (password !== confirmPassword) {
    error.textContent = "Passwords do not match";
    error.classList.remove("hidden");
    return;
  }

  try {
    await Auth.signUp(email, password);
  } catch (err) {
    if (err.code !== "UsernameExistsException") {
      error.textContent = err.message;
      error.classList.remove("hidden");
      return;
    }
  }

  _pendingEmail = email;
  hideAll();
  _root.querySelector("#confirm-card").classList.remove("hidden");
  _root.querySelector("#confirm-email-display").textContent = email;
}

async function handleConfirm(e) {
  e.preventDefault();
  const error = _root.querySelector("#confirm-error");
  error.classList.add("hidden");

  const code = _root.querySelector("#confirm-code").value.trim();

  try {
    await Auth.confirmSignUp(_pendingEmail, code);
    const password = _root.querySelector("#sign-up-password").value;
    const result = await Auth.signIn(_pendingEmail, password);

    if (result.challenge === "MFA_SETUP") {
      _mfaSession = result.session;
      await showMfaSetupCard(result.session);
      return;
    }
    if (result.challenge === "SOFTWARE_TOKEN_MFA") {
      _mfaSession = result.session;
      hideAll();
      _root.querySelector("#mfa-card").classList.remove("hidden");
      return;
    }

    Session.save({ ...result, email: _pendingEmail });
    if (_onLogin) _onLogin();
  } catch {
    error.textContent = "Invalid code. Please check your email and try again.";
    error.classList.remove("hidden");
  }
}

async function showMfaSetupCard(session) {
  hideAll();
  _root.querySelector("#mfa-setup-card").classList.remove("hidden");

  try {
    const resp = await Auth.associateSoftwareToken(session);
    _mfaSession = resp.Session;
    const secret = resp.SecretCode;
    const otpUri = `otpauth://totp/DocumentAI:${_pendingEmail}?secret=${secret}&issuer=DocumentAI`;
    _root.querySelector("#mfa-secret-code").textContent = secret;
    const canvas = _root.querySelector("#mfa-qr-canvas");
    await QRCode.toCanvas(canvas, otpUri, { width: 200, margin: 2 });
  } catch (err) {
    const error = _root.querySelector("#mfa-setup-error");
    error.textContent = err.message;
    error.classList.remove("hidden");
  }
}

async function handleMfaVerify(e) {
  e.preventDefault();
  const error = _root.querySelector("#mfa-error");
  error.classList.add("hidden");

  const code = _root.querySelector("#mfa-code").value.trim();

  try {
    const tokens = await Auth.respondToMfaChallenge(_mfaSession, code, _pendingEmail);
    Session.save({ ...tokens, email: _pendingEmail });
    if (_onLogin) _onLogin();
  } catch (err) {
    if (err.code === "NotAuthorizedException") {
      error.textContent = "Session expired. Please sign in again.";
      error.classList.remove("hidden");
      setTimeout(() => reset(), 2000);
      return;
    }
    error.textContent = err.code === "CodeMismatchException" ? "Invalid code." : err.message;
    error.classList.remove("hidden");
  }
}

async function handleMfaSetupVerify(e) {
  e.preventDefault();
  const error = _root.querySelector("#mfa-setup-error");
  error.classList.add("hidden");

  const code = _root.querySelector("#mfa-setup-code").value.trim();

  try {
    const tokens = await Auth.verifySoftwareToken(_mfaSession, code, _pendingEmail);
    Session.save({ ...tokens, email: _pendingEmail });
    if (_onLogin) _onLogin();
  } catch (err) {
    if (err.code === "NotAuthorizedException") {
      error.textContent = "Session expired. Please sign in again.";
      error.classList.remove("hidden");
      setTimeout(() => reset(), 2000);
      return;
    }
    error.textContent = err.code === "CodeMismatchException" ? "Invalid code." : err.message;
    error.classList.remove("hidden");
  }
}

async function handleForgotPassword(e) {
  e.preventDefault();
  const error = _root.querySelector("#forgot-password-error");
  error.classList.add("hidden");

  const email = _root.querySelector("#forgot-email").value.trim();
  if (!email) {
    error.textContent = "Email is required";
    error.classList.remove("hidden");
    return;
  }

  try {
    await Auth.forgotPassword(email);
  } catch {
    // Don't reveal user existence
  }
  _pendingEmail = email;
  hideAll();
  _root.querySelector("#reset-password-card").classList.remove("hidden");
}

async function handleResetPassword(e) {
  e.preventDefault();
  const error = _root.querySelector("#reset-password-error");
  error.classList.add("hidden");

  const code = _root.querySelector("#reset-code").value.trim();
  const newPassword = _root.querySelector("#reset-new-password").value;
  const confirmPassword = _root.querySelector("#reset-confirm-password").value;

  if (newPassword !== confirmPassword) {
    error.textContent = "Passwords do not match";
    error.classList.remove("hidden");
    return;
  }

  try {
    await Auth.confirmForgotPassword(_pendingEmail, code, newPassword);
    const result = await Auth.signIn(_pendingEmail, newPassword);

    if (result.challenge === "SOFTWARE_TOKEN_MFA") {
      _mfaSession = result.session;
      hideAll();
      _root.querySelector("#mfa-card").classList.remove("hidden");
      return;
    }

    Session.save({ ...result, email: _pendingEmail });
    if (_onLogin) _onLogin();
  } catch (err) {
    error.textContent = err.message;
    error.classList.remove("hidden");
  }
}
