import * as Auth from "../services/auth.js";
import * as Session from "../utils/session.js";

let _onLogin = null;
let _pendingEmail = null;

export function init({ onLogin }) {
  _onLogin = onLogin;

  const signInCard = document.getElementById("sign-in-card");
  const signUpCard = document.getElementById("sign-up-card");
  const confirmCard = document.getElementById("confirm-card");
  const helperSignIn = document.getElementById("helper-sign-in");
  const helperSignUp = document.getElementById("helper-sign-up");

  // Sign In form
  document.getElementById("sign-in-form").addEventListener("submit", handleSignIn);

  // Sign Up form
  document.getElementById("sign-up-form").addEventListener("submit", handleSignUp);

  // Confirm form
  document.getElementById("confirm-form").addEventListener("submit", handleConfirm);

  // Toggle between sign in / sign up
  document.getElementById("show-sign-up").addEventListener("click", (e) => {
    e.preventDefault();
    signInCard.classList.add("hidden");
    signUpCard.classList.remove("hidden");
    confirmCard.classList.add("hidden");
    if (helperSignIn) helperSignIn.classList.add("hidden");
    if (helperSignUp) helperSignUp.classList.remove("hidden");
  });

  document.getElementById("show-sign-in").addEventListener("click", (e) => {
    e.preventDefault();
    signUpCard.classList.add("hidden");
    confirmCard.classList.add("hidden");
    signInCard.classList.remove("hidden");
    if (helperSignUp) helperSignUp.classList.add("hidden");
    if (helperSignIn) helperSignIn.classList.remove("hidden");
  });

  reset();

  // Show/hide password toggles
  document.querySelectorAll(".show-password").forEach((btn) => {
    btn.addEventListener("click", () => {
      const input = document.getElementById(btn.dataset.target);
      if (!input) return;
      const showing = input.type === "text";
      input.type = showing ? "password" : "text";
      btn.textContent = showing ? "Show password" : "Hide password";
    });
  });
}

export function reset() {
  document.getElementById("sign-in-card").classList.remove("hidden");
  document.getElementById("sign-up-card").classList.add("hidden");
  document.getElementById("confirm-card").classList.add("hidden");
  ["sign-in-form", "sign-up-form", "confirm-form"].forEach((id) => {
    const form = document.getElementById(id);
    if (form) form.reset();
  });
  ["sign-in-error", "sign-up-error", "confirm-error"].forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.classList.add("hidden");
  });
  _pendingEmail = null;
}

async function handleSignIn(e) {
  e.preventDefault();
  const error = document.getElementById("sign-in-error");
  error.classList.add("hidden");

  const email = document.getElementById("sign-in-email").value.trim();
  const password = document.getElementById("sign-in-password").value;

  try {
    const tokens = await Auth.signIn(email, password);
    Session.save({ ...tokens, email });
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
  const error = document.getElementById("sign-up-error");
  error.classList.add("hidden");

  const email = document.getElementById("sign-up-email").value.trim();
  const password = document.getElementById("sign-up-password").value;
  const confirmPassword = document.getElementById("sign-up-password-confirm").value;

  if (password !== confirmPassword) {
    error.textContent = "Passwords do not match";
    error.classList.remove("hidden");
    return;
  }

  try {
    await Auth.signUp(email, password);
  } catch (err) {
    // Swallow UsernameExistsException to prevent user enumeration —
    // fall through to the confirm screen as if signup succeeded.
    // Proper mitigation requires a Cognito PreSignUp/CustomMessage Lambda
    // to email existing users a "you already have an account" notice.
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
  document.getElementById("sign-up-card").classList.add("hidden");
  document.getElementById("confirm-card").classList.remove("hidden");
  document.getElementById("confirm-email-display").textContent = email;
  const helperSignUp = document.getElementById("helper-sign-up");
  if (helperSignUp) helperSignUp.classList.add("hidden");
}

async function handleConfirm(e) {
  e.preventDefault();
  const error = document.getElementById("confirm-error");
  error.classList.add("hidden");

  const code = document.getElementById("confirm-code").value.trim();

  try {
    await Auth.confirmSignUp(_pendingEmail, code);

    // Auto sign in after confirmation
    const password = document.getElementById("sign-up-password").value;
    const tokens = await Auth.signIn(_pendingEmail, password);
    Session.save({ ...tokens, email: _pendingEmail });
    if (_onLogin) _onLogin();
  } catch (err) {
    // Generic message so the confirm step doesn't reveal whether the
    // account exists, is already confirmed, or the code is simply wrong.
    error.textContent = "That code didn't work. Please check your email and try again.";
    error.classList.remove("hidden");
  }
}
