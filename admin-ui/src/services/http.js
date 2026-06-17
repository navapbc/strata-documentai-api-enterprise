let _refreshing = null;

async function _tryRefresh() {
  if (_refreshing) return _refreshing;
  _refreshing = (async () => {
    try {
      const { refreshSession } = await import("./auth.js");
      const session = JSON.parse(sessionStorage.getItem("docai_console_session"));
      if (!session?.refreshToken) throw new Error("No refresh token");
      const tokens = await refreshSession(session.refreshToken);
      const { update } = await import("../utils/session.js");
      update(tokens);
      _jwt = tokens.idToken;
      return true;
    } catch {
      sessionStorage.removeItem("docai_console_session");
      window.location.reload();
      return false;
    } finally {
      _refreshing = null;
    }
  })();
  return _refreshing;
}

function createClient(buildAuthHeaders) {
  let baseUrl = "";

  return {
    configure(url) {
      baseUrl = url.replace(/\/$/, "");
    },
    getBaseUrl() {
      return baseUrl;
    },

    async request(method, path, body = null, _retried = false) {
      const url = `${baseUrl}${path}`;
      const opts = {
        method,
        headers: { ...buildAuthHeaders(), "Content-Type": "application/json" },
      };
      if (body) opts.body = JSON.stringify(body);

      let res;
      try {
        res = await fetch(url, opts);
      } catch (e) {
        console.error("Network error calling", url, e);
        throw new Error(
          `Cannot reach API at ${baseUrl} - check CORS and that the endpoint is reachable.`,
        );
      }

      if (!res.ok) {
        if (res.status === 401 && !_retried) {
          const refreshed = await _tryRefresh();
          if (refreshed) return this.request(method, path, body, true);
          return;
        }
        const respBody = await res.json().catch(() => ({ detail: res.statusText }));
        const detail = respBody.detail || respBody.message || res.statusText;
        const err = new Error(detail);
        err.status = res.status;
        err.method = method;
        err.path = path;
        throw err;
      }
      return res.json();
    },
  };
}

let _jwt = "";
let _apiKey = "";

export function setJwt(token) {
  _jwt = token;
}
export function setApiKey(key) {
  _apiKey = key;
}

export const adminClient = createClient(() => ({ Authorization: `Bearer ${_jwt}` }));
export const dataClient = createClient(() => ({ "API-Key": _apiKey }));

export function configure({ baseUrl, jwt, apiKey }) {
  if (baseUrl !== undefined) {
    adminClient.configure(baseUrl);
    dataClient.configure(baseUrl);
  }
  if (jwt !== undefined) _jwt = jwt;
  if (apiKey !== undefined) _apiKey = apiKey;
}
