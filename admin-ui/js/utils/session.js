const STORAGE_KEY = "docai_console_session";
const INACTIVITY_TIMEOUT_MS = 15 * 60 * 1000; // 15 minutes

let _inactivityTimer = null;
let _onExpire = null;

export function get() {
  try {
    return JSON.parse(sessionStorage.getItem(STORAGE_KEY));
  } catch {
    return null;
  }
}

export function save({ accessToken, idToken, refreshToken, email, expiresIn }) {
  const session = {
    accessToken,
    idToken,
    refreshToken,
    email,
    expiresAt: Date.now() + expiresIn * 1000,
  };
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify(session));
  resetInactivityTimer();
  return session;
}

export function update({ accessToken, idToken, expiresIn }) {
  const session = get();
  if (!session) return null;
  session.accessToken = accessToken;
  session.idToken = idToken;
  session.expiresAt = Date.now() + expiresIn * 1000;
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify(session));
  return session;
}

export function clear() {
  sessionStorage.removeItem(STORAGE_KEY);
  stopInactivityTimer();
}

export function isExpired() {
  const session = get();
  if (!session) return true;
  return Date.now() >= session.expiresAt;
}

export function getAccessToken() {
  const session = get();
  return session?.accessToken || null;
}

export function getEmail() {
  const session = get();
  return session?.email || null;
}

function decodeJwt(token) {
  try {
    const payload = token.split(".")[1];
    const padded = payload + "=".repeat((4 - (payload.length % 4)) % 4);
    return JSON.parse(atob(padded.replace(/-/g, "+").replace(/_/g, "/")));
  } catch {
    return null;
  }
}

export function getRoles() {
  const session = get();
  if (!session?.idToken) return [];
  const claims = decodeJwt(session.idToken);
  const groups = claims?.["cognito:groups"];
  if (!groups) return [];
  return Array.isArray(groups) ? groups : [groups];
}

export function isApproved() {
  const roles = getRoles();
  return roles.includes("super-admin") || roles.includes("tenant-admin");
}

export function isSuperAdmin() {
  return getRoles().includes("super-admin");
}

export function onExpire(callback) {
  _onExpire = callback;
}

function resetInactivityTimer() {
  stopInactivityTimer();
  _inactivityTimer = setTimeout(async () => {
    const session = get();
    if (session?.accessToken) {
      try {
        const { signOut } = await import("../services/auth.js");
        await signOut(session.accessToken);
      } catch {
        // best-effort server-side revocation
      }
    }
    clear();
    if (_onExpire) _onExpire();
  }, INACTIVITY_TIMEOUT_MS);
}

function stopInactivityTimer() {
  if (_inactivityTimer) {
    clearTimeout(_inactivityTimer);
    _inactivityTimer = null;
  }
}

// Reset timer on user activity
["click", "keydown", "mousemove", "scroll"].forEach((event) => {
  document.addEventListener(
    event,
    () => {
      if (sessionStorage.getItem(STORAGE_KEY)) {
        resetInactivityTimer();
      }
    },
    { passive: true },
  );
});
