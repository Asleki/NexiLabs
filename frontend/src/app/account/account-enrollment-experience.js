/** P006.UI.10.4 — Frontend-only enrollment presentation; no API, DB or credential authority. */
import {
  AccountEnrollmentRoute,
  accountEnrollmentRouteFromHash,
  accountEnrollmentRouteToHash,
  isAccountEnrollmentRoute,
} from "./account-enrollment-route.js";
import {
  accountEnrollmentGatewayMarkup,
  accountEnrollmentHomeEntryMarkup,
} from "../../ui/pages/account-enrollment-gateway.js";
import {
  guestAccountCreateMarkup,
  guestEmailVerificationMarkup,
  guestAccountCompleteMarkup,
} from "../../ui/pages/guest-account-enrollment.js";
import {
  developerAccessRequestMarkup,
  developerRequestReceivedMarkup,
  developerSetupVerificationMarkup,
  developerRegistrationMarkup,
  developerEmailVerificationMarkup,
  developerEnigmaProvisioningMarkup,
  developerAccountCompleteMarkup,
} from "../../ui/pages/developer-account-enrollment-p006-ui-10-4.js";

const HOME_HASH = "#/runtime";
const STYLE_HREF = "./styles/account-enrollment-v1.css";
const FOUNDATION_MESSAGE = "This frontend foundation does not submit or retain account data. Production account authority is implemented in a later milestone.";

function routeMarkup(route) {
  switch (route) {
    case AccountEnrollmentRoute.GATEWAY: return accountEnrollmentGatewayMarkup();
    case AccountEnrollmentRoute.GUEST_CREATE: return guestAccountCreateMarkup();
    case AccountEnrollmentRoute.GUEST_VERIFY_EMAIL: return guestEmailVerificationMarkup();
    case AccountEnrollmentRoute.GUEST_COMPLETE: return guestAccountCompleteMarkup();
    case AccountEnrollmentRoute.DEVELOPER_REQUEST: return developerAccessRequestMarkup();
    case AccountEnrollmentRoute.DEVELOPER_REQUESTED: return developerRequestReceivedMarkup();
    case AccountEnrollmentRoute.DEVELOPER_VERIFY_SETUP: return developerSetupVerificationMarkup();
    case AccountEnrollmentRoute.DEVELOPER_REGISTER: return developerRegistrationMarkup();
    case AccountEnrollmentRoute.DEVELOPER_VERIFY_EMAIL: return developerEmailVerificationMarkup();
    case AccountEnrollmentRoute.DEVELOPER_ENIGMA: return developerEnigmaProvisioningMarkup();
    case AccountEnrollmentRoute.DEVELOPER_COMPLETE: return developerAccountCompleteMarkup();
    default: return null;
  }
}

function ensureStylesheet(documentRef) {
  if (documentRef.querySelector?.("link[data-account-enrollment-styles='true']")) return false;
  const link = documentRef.createElement?.("link");
  if (!link) return false;
  link.rel = "stylesheet";
  link.href = STYLE_HREF;
  link.dataset.accountEnrollmentStyles = "true";
  documentRef.head?.appendChild?.(link);
  return true;
}

function ensureHomeEntry(documentRef, hash) {
  if (String(hash || "").trim() !== HOME_HASH) return false;
  const gateway = documentRef.querySelector?.(".runtime-gateway");
  if (!gateway || gateway.querySelector?.("[data-account-enrollment-entry]")) return false;
  gateway.insertAdjacentHTML?.("beforeend", accountEnrollmentHomeEntryMarkup());
  return true;
}

export function installAccountEnrollmentExperience({
  documentRef = globalThis.document,
  windowRef = globalThis.window,
} = {}) {
  if (!documentRef?.querySelector) throw new TypeError("documentRef must provide querySelector");
  if (!windowRef?.location) throw new TypeError("windowRef.location is required");

  ensureStylesheet(documentRef);

  const outlet = () => documentRef.querySelector("[data-role='application-page']");
  const root = () => documentRef.querySelector("#nexilabs-app");

  const render = () => {
    const hash = String(windowRef.location.hash || "").trim();
    const route = accountEnrollmentRouteFromHash(hash);
    const appRoot = root();

    if (route) {
      const target = outlet();
      if (!target) return false;
      target.innerHTML = routeMarkup(route);
      if (appRoot) appRoot.dataset.accountEnrollmentRoute = route;
      documentRef.querySelector?.("#main-content")?.focus?.({ preventScroll: true });
      return true;
    }

    if (appRoot) delete appRoot.dataset.accountEnrollmentRoute;
    return ensureHomeEntry(documentRef, hash);
  };

  const onClick = (event) => {
    const accountTarget = event.target?.closest?.("[data-account-route]");
    if (accountTarget) {
      const route = accountTarget.dataset.accountRoute;
      if (!isAccountEnrollmentRoute(route)) return;
      event.preventDefault?.();
      windowRef.location.hash = accountEnrollmentRouteToHash(route);
      render();
      return;
    }

    const homeTarget = event.target?.closest?.("[data-route='runtime-gateway']");
    if (homeTarget) queueMicrotask(render);
  };

  const onSubmit = (event) => {
    const form = event.target?.closest?.("[data-account-foundation-form]");
    if (!form) return;
    event.preventDefault?.();
    const message = form.querySelector?.("[data-account-authority-message]");
    if (message) message.textContent = FOUNDATION_MESSAGE;
  };

  const onHashChange = () => queueMicrotask(render);

  documentRef.addEventListener?.("click", onClick);
  documentRef.addEventListener?.("submit", onSubmit);
  windowRef.addEventListener?.("hashchange", onHashChange);
  render();

  return Object.freeze({
    render,
    dispose() {
      documentRef.removeEventListener?.("click", onClick);
      documentRef.removeEventListener?.("submit", onSubmit);
      windowRef.removeEventListener?.("hashchange", onHashChange);
    },
  });
}

export { FOUNDATION_MESSAGE as ACCOUNT_ENROLLMENT_FOUNDATION_MESSAGE };
