import * as Session from "../../shared/utils/session.js";
import * as Toast from "../../shared/utils/toast.js";
import * as HttpClient from "../../shared/services/http.js";
import * as Auth from "../../shared/services/auth.js";

import * as LoginView from "./views/login/login.js";
import * as UploadView from "./views/upload/upload.js";

let CONFIG = {
  apiUrl: "",
  cognitoUserPoolId: "",
  cognitoClientId: "",
  cognitoDomain: null,
  googleEnabled: false,
};

async function loadConfig() {
  try {
    const response = await fetch("config.json");
    const outputs = await response.json();
    CONFIG.apiUrl = outputs.api_endpoint?.value || "";
    CONFIG.cognitoUserPoolId = outputs.cognito_user_pool_id?.value || "";
    CONFIG.cognitoClientId = outputs.cognito_client_id?.value || "";
    CONFIG.cognitoDomain = outputs.cognito_domain?.value || null;
    CONFIG.googleEnabled = outputs.cognito_google_enabled?.value === true;
  } catch {
    CONFIG.apiUrl = "http://localhost:8000";
  }
}

const app = document.getElementById("app");

function showLogin() {
  LoginView.mount(app, {
    googleEnabled: CONFIG.googleEnabled,
    cognitoDomain: CONFIG.cognitoDomain,
    cognitoClientId: CONFIG.cognitoClientId,
    redirectUri: window.location.origin + "/callback",
  });
}

function showApp(session) {
  HttpClient.configure({ baseUrl: CONFIG.apiUrl, jwt: session.idToken, apiKey: "" });
  UploadView.mount(app);
}

async function logout() {
  const session = Session.get();
  if (session?.accessToken) {
    try {
      await Auth.signOut(session.accessToken);
    } catch {
      // ignore
    }
  }
  Session.clear();
  showLogin();
}

async function init() {
  await loadConfig();
  Auth.configure(CONFIG.cognitoUserPoolId, CONFIG.cognitoClientId);

  // Handle OAuth callback (Google SSO redirect)
  const isCallback = window.location.pathname === "/callback";
  const params = new URLSearchParams(window.location.search);
  const authCode = params.get("code");
  const returnedState = params.get("state");
  if (isCallback && authCode && CONFIG.cognitoDomain) {
    const savedState = sessionStorage.getItem("oauth_state");
    const codeVerifier = sessionStorage.getItem("oauth_code_verifier");
    sessionStorage.removeItem("oauth_state");
    sessionStorage.removeItem("oauth_code_verifier");

    if (!savedState || savedState !== returnedState) {
      console.error("OAuth state mismatch - possible CSRF");
      window.history.replaceState({}, "", "/");
      showLogin();
      return;
    }

    try {
      const tokens = await Auth.exchangeCodeForTokens(
        authCode,
        CONFIG.cognitoDomain,
        CONFIG.cognitoClientId,
        window.location.origin + "/callback",
        codeVerifier,
      );
      Session.save({
        accessToken: tokens.access_token,
        idToken: tokens.id_token,
        refreshToken: tokens.refresh_token,
        expiresIn: tokens.expires_in,
        email: tokens.email,
      });
      window.history.replaceState({}, "", "/");
      showApp(Session.get());
      return;
    } catch (e) {
      console.error("OAuth callback failed:", e);
      window.history.replaceState({}, "", "/");
    }
  }

  const session = Session.get();
  if (session && !Session.isExpired()) {
    showApp(session);
  } else {
    Session.clear();
    showLogin();
  }
}

LoginView.onLoginSuccess(() => {
  const session = Session.get();
  showApp(session);
});

UploadView.onLogout(() => logout());

Session.onExpire(() => {
  showLogin();
  Toast.show("Session expired due to inactivity");
});

init();
