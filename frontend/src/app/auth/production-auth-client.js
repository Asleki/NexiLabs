/** P006.UI.10.3 — Browser client for the local Production authentication authority. */
import { AuthenticationClientError } from "./development-auth-client.js";

export function defaultProductionAuthBase(windowRef = globalThis.window) {
  const hostname = windowRef?.location?.hostname || "127.0.0.1";
  return `http://${hostname}:8767`;
}

export function createProductionAuthClient({
  fetchRef = globalThis.fetch,
  windowRef = globalThis.window,
  baseUrl = defaultProductionAuthBase(windowRef),
} = {}) {
  if (typeof fetchRef !== "function") throw new TypeError("fetchRef must be a function");

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

  return Object.freeze({
    startDeveloper: ({ username, password, runtime }) =>
      request("/auth/developer/start", { method: "POST", body: { username, password, runtime } }),
    verifyDeveloper: ({ attemptId, response }) =>
      request("/auth/developer/enigma", { method: "POST", body: { attemptId, response } }),
    session: (token) => request("/auth/session", { token }),
    logout: (token) => request("/auth/logout", { method: "POST", token }),
    adminEligibility: (token) => request("/admin/eligibility", { token }),
    startAdminElevation: (token, { adminEmail, adminPassword }) =>
      request("/admin/elevate", { method: "POST", token, body: { adminEmail, adminPassword } }),
    verifyAdminElevation: (token, { attemptId, response }) =>
      request("/admin/elevate/enigma", { method: "POST", token, body: { attemptId, response } }),
    revokeAdminElevation: (token, elevationId) =>
      request("/admin/elevation/logout", { method: "POST", token, body: { elevationId } }),
  });
}
