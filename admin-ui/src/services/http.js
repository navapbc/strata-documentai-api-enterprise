function createClient(buildAuthHeaders) {
  let baseUrl = "";

  return {
    configure(url) {
      baseUrl = url.replace(/\/$/, "");
    },
    getBaseUrl() {
      return baseUrl;
    },

    async request(method, path, body = null) {
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
        if (res.status === 401) {
          // Token expired - clear session and redirect to login
          sessionStorage.removeItem("docai_console_session");
          window.location.reload();
          return;
        }
        const body = await res.json().catch(() => ({ detail: res.statusText }));
        const detail = body.detail || body.message || res.statusText;
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
