/** P006.UI.10.4 — Runtime-aware auth transport over the locked authentication orchestration. */
import { createDevelopmentAuthClient } from "./development-auth-client.js";
import { createProductionAuthClient } from "./production-auth-client-p006-ui-10-4.js";

export function createRuntimeAuthClient({ fetchRef = globalThis.fetch, windowRef = globalThis.window } = {}) {
  const development = createDevelopmentAuthClient({ fetchRef, windowRef });
  const production = createProductionAuthClient({ fetchRef, windowRef });
  let pendingDeveloperAuthority = "development";

  const isProductionToken = (token) => String(token || "").startsWith("prod-session:");

  return Object.freeze({
    // Guest persistence/cutover remains deliberately outside P006.UI.10.4.
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
