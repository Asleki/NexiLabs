/** P006.UI.10.4 — Same-origin Production authentication client. */
import { AuthenticationClientError } from "./development-auth-client.js";

const LOOPBACK_HOSTS = new Set(["127.0.0.1", "localhost", "::1", "[::1]"]);

export function defaultProductionAuthBase(windowRef = globalThis.window) {
  const location = windowRef?.location;
  const hostname = String(location?.hostname || "127.0.0.1").toLowerCase();
  const protocol = String(location?.protocol || "http:").toLowerCase();
  if (protocol === "http:" && LOOPBACK_HOSTS.has(hostname)) {
    const host = hostname === "::1" ? "[::1]" : hostname;
    return `http://${host}:8767`;
  }
  return "";
}

function directLockedAuthority(baseUrl) {
  try {
    const parsed = new URL(baseUrl);
    return parsed.protocol === "http:"
      && LOOPBACK_HOSTS.has(parsed.hostname)
      && parsed.port === "8767";
  } catch {
    return false;
  }
}

export function createProductionAuthClient({
  fetchRef = globalThis.fetch,
  windowRef = globalThis.window,
  baseUrl = defaultProductionAuthBase(windowRef),
} = {}) {
  if (typeof fetchRef !== "function") throw new TypeError("fetchRef must be a function");
  const direct = directLockedAuthority(baseUrl);

  const request = async (path, { method = "GET", body, token } = {}) => {
    const headers = { Accept: "application/json" };
    if (body !== undefined) headers["Content-Type"] = "application/json";
    if (token) headers.Authorization = `Bearer ${token}`;
    let response;
    try {
      response = await fetchRef(`${baseUrl}${path}`, {
        method,
        headers,
        body: body === undefined ? undefined : JSON.stringify(body),
        cache: "no-store",
        credentials: "same-origin",
      });
    } catch {
      throw new AuthenticationClientError("Production authentication authority is unavailable.");
    }
    const payload = await response.json().catch(() => ({}));
    if (!response.ok || payload.ok === false) {
      throw new AuthenticationClientError(payload.error || "Production authentication request rejected.", { status: response.status });
    }
    return payload;
  };

  const adminPath = (suffix) => direct ? `/admin/${suffix}` : `/auth/admin/${suffix}`;

  return Object.freeze({
    startDeveloper: ({ username, password, runtime }) =>
      request("/auth/developer/start", { method: "POST", body: { username, password, runtime } }),
    verifyDeveloper: ({ attemptId, response }) =>
      request("/auth/developer/enigma", { method: "POST", body: { attemptId, response } }),
    session: (token) => request("/auth/session", { token }),
    logout: (token) => request("/auth/logout", { method: "POST", token }),
    adminEligibility: (token) => request(adminPath("eligibility"), { token }),
    startAdminElevation: (token, { adminEmail, adminPassword }) =>
      request(adminPath("elevate"), { method: "POST", token, body: { adminEmail, adminPassword } }),
    verifyAdminElevation: (token, { attemptId, response }) =>
      request(adminPath("elevate/enigma"), { method: "POST", token, body: { attemptId, response } }),
    revokeAdminElevation: (token, elevationId) =>
      request(adminPath("elevation/logout"), { method: "POST", token, body: { elevationId } }),
  });
}
