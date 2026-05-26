import * as Auth from "../../services/auth.js";
import * as Session from "../../utils/session.js";
import QRCode from "qrcode";
import { tpl } from "../../utils/tpl.js";
import html from "./login.html";

const tmpl = tpl(html);

let _onLogin = null;
let _pendingEmail = null;
let _mfaSession = null;
let _root = null;

export function onLoginSuccess(callback) {
  _onLogin = callback;
}

export function mount(root) {
  _root = root;
  root.replaceChildren(tmpl());

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
    root.querySelector("#confirm-card").classList.add("hidden");
  });

  root.querySelector("#show-sign-in").addEventListener("click", (e) => {
    e.preventDefault();
    root.querySelector("#sign-up-card").classList.add("hidden");
    root.querySelector("#confirm-card").classList.add("hidden");
    root.querySelector("#forgot-password-card").classList.add("hidden");
    root.querySelector("#reset-password-card").classList.add("hidden");
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

function reset() {
  if (!_root) return;
  _root.querySelector("#sign-in-card").classList.remove("hidden");
  _root.querySelector("#sign-up-card").classList.add("hidden");
  _root.querySelector("#confirm-card").classList.add("hidden");
  _root.querySelector("#mfa-card").classList.add("hidden");
  _root.querySelector("#mfa-setup-card").classList.add("hidden");
  _root.querySelector("#forgot-password-card").classList.add("hidden");
  _root.querySelector("#reset-password-card").classList.add("hidden");
  [
    "sign-in-form",
    "sign-up-form",
    "confirm-form",
    "mfa-form",
    "mfa-setup-form",
    "forgot-password-form",
    "reset-password-form",
  ].forEach((id) => {
    const form = _root.querySelector(`#${id}`);
    if (form) form.reset();
  });
  [
    "sign-in-error",
    "sign-up-error",
    "confirm-error",
    "mfa-error",
    "mfa-setup-error",
    "forgot-password-error",
    "reset-password-error",
  ].forEach((id) => {
    const el = _root.querySelector(`#${id}`);
    if (el) el.classList.add("hidden");
  });
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
      showMfaCard();
      return;
    }

    if (result.challenge === "MFA_SETUP") {
      _pendingEmail = email;
      _mfaSession = result.session;
      await showMfaSetupCard(result.session);
      return;
    }

    Session.save({
      accessToken: result.accessToken,
      idToken: result.idToken,
      refreshToken: result.refreshToken,
      expiresIn: result.expiresIn,
      email,
    });
    if (_onLogin) _onLogin();
  } catch (err) {
    if (err.code === "NotAuthorizedException" || err.code === "UserNotFoundException") {
      error.textContent = "Incorrect email or password";
    } else if (err.code === "UserNotConfirmedException") {
      error.textContent = "Please confirm your email first";
    } else if (err.code === "ResourceNotFoundException") {
      error.textContent = "Service not configured. Please contact an administrator.";
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
      if (err.code === "InvalidPasswordException") {
        error.textContent = "Password must be at least 12 characters";
      } else if (err.code === "ResourceNotFoundException") {
        error.textContent = "Service not configured. Please contact an administrator.";
      } else {
        error.textContent = err.message;
      }
      error.classList.remove("hidden");
      return;
    }
  }

  _pendingEmail = email;
  _root.querySelector("#sign-up-card").classList.add("hidden");
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
      showMfaCard();
      return;
    }

    Session.save({
      accessToken: result.accessToken,
      idToken: result.idToken,
      refreshToken: result.refreshToken,
      expiresIn: result.expiresIn,
      email: _pendingEmail,
    });
    if (_onLogin) _onLogin();
  } catch (err) {
    error.textContent = "That code didn't work. Please check your email and try again.";
    error.classList.remove("hidden");
  }
}

function showMfaCard() {
  _root.querySelector("#sign-in-card").classList.add("hidden");
  _root.querySelector("#sign-up-card").classList.add("hidden");
  _root.querySelector("#confirm-card").classList.add("hidden");
  _root.querySelector("#mfa-card").classList.remove("hidden");
  _root.querySelector("#mfa-setup-card").classList.add("hidden");
}

async function showMfaSetupCard(session) {
  _root.querySelector("#sign-in-card").classList.add("hidden");
  _root.querySelector("#sign-up-card").classList.add("hidden");
  _root.querySelector("#confirm-card").classList.add("hidden");
  _root.querySelector("#mfa-card").classList.add("hidden");
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
    } else if (err.code === "CodeMismatchException") {
      error.textContent = "Invalid code. Please try again.";
    } else {
      error.textContent = err.message;
    }
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
    } else if (err.code === "CodeMismatchException") {
      error.textContent = "Invalid code. Please try again.";
    } else {
      error.textContent = err.message;
    }
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
    _pendingEmail = email;
    _root.querySelector("#forgot-password-card").classList.add("hidden");
    _root.querySelector("#reset-password-card").classList.remove("hidden");
  } catch (err) {
    if (err.code === "UserNotFoundException") {
      // Don't reveal whether user exists — show success anyway
      _pendingEmail = email;
      _root.querySelector("#forgot-password-card").classList.add("hidden");
      _root.querySelector("#reset-password-card").classList.remove("hidden");
    } else if (err.code === "LimitExceededException") {
      error.textContent = "Too many attempts. Please try again later.";
      error.classList.remove("hidden");
    } else {
      error.textContent = err.message;
      error.classList.remove("hidden");
    }
  }
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
    // Auto sign-in after reset
    const result = await Auth.signIn(_pendingEmail, newPassword);

    if (result.challenge === "SOFTWARE_TOKEN_MFA") {
      _mfaSession = result.session;
      _root.querySelector("#reset-password-card").classList.add("hidden");
      showMfaCard();
      return;
    }

    Session.save({ ...result, email: _pendingEmail });
    if (_onLogin) _onLogin();
  } catch (err) {
    if (err.code === "CodeMismatchException" || err.code === "ExpiredCodeException") {
      error.textContent = "Invalid or expired code. Please request a new one.";
    } else if (err.code === "InvalidPasswordException") {
      error.textContent = "Password must be at least 12 characters.";
    } else {
      error.textContent = err.message;
    }
    error.classList.remove("hidden");
  }
}
