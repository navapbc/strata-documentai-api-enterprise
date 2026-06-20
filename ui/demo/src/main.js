import * as Session from "../../shared/utils/session.js";
import * as Toast from "../../shared/utils/toast.js";
import * as HttpClient from "../../shared/services/http.js";
import * as Auth from "../../shared/services/auth.js";

import * as LoginView from "./views/login/login.js";
import * as UploadView from "./views/upload/upload.js";

let CONFIG = { apiUrl: "", cognitoUserPoolId: "", cognitoClientId: "" };

async function loadConfig() {
  try {
    const response = await fetch("config.json");
    const outputs = await response.json();
    CONFIG.apiUrl = outputs.api_endpoint?.value || "";
    CONFIG.cognitoUserPoolId = outputs.cognito_user_pool_id?.value || "";
    CONFIG.cognitoClientId = outputs.cognito_client_id?.value || "";
  } catch {
    CONFIG.apiUrl = "http://localhost:8000";
  }
}

const app = document.getElementById("app");

function showLogin() {
  LoginView.mount(app);
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
