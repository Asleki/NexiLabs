/** P006.UI.10.3 — Runtime-aware auth transport without changing locked auth orchestration. */
import { createDevelopmentAuthClient } from "./development-auth-client.js";
import { createProductionAuthClient } from "./production-auth-client.js";

export function createRuntimeAuthClient({ fetchRef = globalThis.fetch, windowRef = globalThis.window } = {}) {
  const development = createDevelopmentAuthClient({ fetchRef, windowRef });
  const production = createProductionAuthClient({ fetchRef, windowRef });
  let pendingDeveloperAuthority = "development";

  const isProductionToken = (token) => String(token || "").startsWith("prod-session:");

  return Object.freeze({
    // Guest persistence/cutover is deliberately outside P006.UI.10.3.
    loginGuest: (input) => development.loginGuest(input),
    async startDeveloper(input) {
      pendingDeveloperAuthority = String(input?.runtime || "").toLowerCase() === "production"
        ? "production"
        : "development";
      return pendingDeveloperAuthority === "production"
        ? production.startDeveloper(input)
        : development.startDeveloper(input);
    },
    verifyDeveloper(input) {
      return pendingDeveloperAuthority === "production"
        ? production.verifyDeveloper(input)
        : development.verifyDeveloper(input);
    },
    session(token) {
      return isProductionToken(token) ? production.session(token) : development.session(token);
    },
    logout(token) {
      return isProductionToken(token) ? production.logout(token) : development.logout(token);
    },
    production,
  });
}
