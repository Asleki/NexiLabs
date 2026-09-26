/** P006.UI.10.4 — Full-view Admin elevation inside an authenticated Production Developer session. */
import { ApplicationRoute } from "../navigation/application-route.js";
import { createProductionAuthClient } from "./production-auth-client-p006-ui-10-4.js";
import { adminEnigmaMarkup, adminLoginMarkup } from "../../ui/pages/admin-login.js";
import { adminWorkspaceMarkup, AdminWorkspaceSection } from "../../ui/pages/admin-workspace.js";
import { AdminReviewStatus } from "../admin/admin-review-view-model.js";

export const AdminPresentation = Object.freeze({
  DEVELOPER: "developer",
  CREDENTIALS: "credentials",
  ENIGMA: "enigma",
  WORKSPACE: "workspace",
});

function formValue(form, name) {
  return String(new FormData(form).get(name) || "").trim();
}

export function installAdminAuthenticationExperience({
  documentRef = globalThis.document,
  windowRef = globalThis.window,
  authentication,
  client = createProductionAuthClient({ windowRef }),
} = {}) {
  if (!authentication?.context) throw new TypeError("authentication context is required");

  let eligibility = null;
  let adminAttempt = null;
  let elevation = null;
  let presentation = AdminPresentation.DEVELOPER;
  let activeSection = AdminWorkspaceSection.OVERVIEW;
  let reviewStatus = AdminReviewStatus.PENDING;
  let refreshGeneration = 0;
  let observer = null;
  let expiryTimer = null;

  const outlet = () => documentRef.querySelector?.("[data-role='application-page']");
  const applicationRoot = () => documentRef.querySelector?.("#nexilabs-app");
  const developerAdminActions = () => documentRef.querySelector?.("[data-role='developer-admin-actions']");

  const observe = () => observer?.observe?.(outlet(), { childList: true, subtree: true });
  const mutatePresentation = (operation) => {
    observer?.disconnect?.();
    try { operation(); } finally { observe(); }
  };

  const clearExpiryTimer = () => {
    if (expiryTimer !== null) {
      windowRef?.clearTimeout?.(expiryTimer);
      expiryTimer = null;
    }
  };

  const resetWorkspaceState = () => {
    activeSection = AdminWorkspaceSection.OVERVIEW;
    reviewStatus = AdminReviewStatus.PENDING;
  };

  const developerSession = () => {
    const session = authentication.context.session;
    return session?.sessionId
      && session.identityType === "nexadevs_developer"
      && session.runtime === "production"
      ? session
      : null;
  };

  const onDeveloperRoute = () =>
    applicationRoot()?.dataset?.applicationRoute === ApplicationRoute.PRODUCTION_DEVELOPER;

  const developerActionMarkup = () => {
    if (!eligibility?.eligible) return "";
    const label = elevation ? "Admin Workspace" : "Admin Access";
    return `<button class="workspace-action admin-access-button" type="button" data-admin-auth-action="enter">${label}</button>`;
  };

  const decorateDeveloperWorkspace = () => {
    const actions = developerAdminActions();
    if (actions) actions.innerHTML = developerActionMarkup();
  };

  const renderDeveloperWorkspace = () => {
    presentation = AdminPresentation.DEVELOPER;
    mutatePresentation(() => {
      authentication.render?.(ApplicationRoute.PRODUCTION_DEVELOPER);
      decorateDeveloperWorkspace();
    });
  };

  const scheduleExpiry = () => {
    clearExpiryTimer();
    if (!elevation?.expiresAt || !windowRef?.setTimeout) return;
    const delay = Math.max(0, Date.parse(elevation.expiresAt) - Date.now());
    expiryTimer = windowRef.setTimeout(async () => {
      const session = developerSession();
      const current = elevation;
      elevation = null;
      adminAttempt = null;
      resetWorkspaceState();
      renderDeveloperWorkspace();
      if (session?.sessionId && current?.elevationId) {
        try { await client.revokeAdminElevation(session.sessionId, current.elevationId); }
        catch { /* expiry remains local even if live revocation is unavailable */ }
      }
    }, Math.min(delay, 2_147_000_000));
  };

  const renderAdminPresentation = ({ error = "" } = {}) => {
    const session = developerSession();
    const target = outlet();
    if (!session || !target || !eligibility?.eligible || !onDeveloperRoute()) {
      clearExpiryTimer();
      return false;
    }
    if (presentation === AdminPresentation.DEVELOPER) {
      mutatePresentation(decorateDeveloperWorkspace);
      clearExpiryTimer();
      return true;
    }
    const markup = presentation === AdminPresentation.WORKSPACE && elevation
      ? adminWorkspaceMarkup({ elevation, activeSection, reviewStatus })
      : presentation === AdminPresentation.ENIGMA && adminAttempt
        ? adminEnigmaMarkup({ challenge: adminAttempt.challenge, error })
        : adminLoginMarkup({ eligibility, error });
    mutatePresentation(() => { target.innerHTML = markup; });
    if (presentation === AdminPresentation.WORKSPACE && elevation) scheduleExpiry();
    else clearExpiryTimer();
    return true;
  };

  const clearAdminState = () => {
    eligibility = null;
    adminAttempt = null;
    elevation = null;
    presentation = AdminPresentation.DEVELOPER;
    resetWorkspaceState();
    clearExpiryTimer();
  };

  const refresh = async () => {
    const generation = ++refreshGeneration;
    const session = developerSession();
    if (!session) {
      clearAdminState();
      return null;
    }
    try {
      const payload = await client.adminEligibility(session.sessionId);
      if (generation !== refreshGeneration) return null;
      eligibility = payload;
      if (!eligibility.eligible) {
        adminAttempt = null;
        elevation = null;
        presentation = AdminPresentation.DEVELOPER;
        resetWorkspaceState();
        clearExpiryTimer();
      }
      if (onDeveloperRoute()) renderAdminPresentation();
      return eligibility;
    } catch {
      if (generation !== refreshGeneration) return null;
      clearAdminState();
      if (onDeveloperRoute()) mutatePresentation(decorateDeveloperWorkspace);
      return null;
    }
  };

  const onSubmit = async (event) => {
    const credentialForm = event.target?.closest?.("[data-admin-auth-form='elevate']");
    const enigmaForm = event.target?.closest?.("[data-admin-auth-form='enigma']");
    const reviewForm = event.target?.closest?.("[data-admin-review-decision-form]");
    if (reviewForm) {
      event.preventDefault();
      return;
    }
    if (!credentialForm && !enigmaForm) return;
    event.preventDefault();
    const session = developerSession();
    if (!session?.sessionId) return;

    if (credentialForm) {
      try {
        const payload = await client.startAdminElevation(session.sessionId, {
          adminEmail: formValue(credentialForm, "adminEmail"),
          adminPassword: formValue(credentialForm, "adminPassword"),
        });
        adminAttempt = { attemptId: payload.attemptId, challenge: payload.challenge };
        elevation = null;
        presentation = AdminPresentation.ENIGMA;
        resetWorkspaceState();
        renderAdminPresentation();
      } catch (error) {
        adminAttempt = null;
        elevation = null;
        presentation = AdminPresentation.CREDENTIALS;
        resetWorkspaceState();
        renderAdminPresentation({ error: error?.message || "Admin login failed." });
      }
      return;
    }

    if (enigmaForm && adminAttempt?.attemptId) {
      try {
        const payload = await client.verifyAdminElevation(session.sessionId, {
          attemptId: adminAttempt.attemptId,
          response: formValue(enigmaForm, "response"),
        });
        adminAttempt = null;
        elevation = payload.elevation;
        presentation = AdminPresentation.WORKSPACE;
        resetWorkspaceState();
        renderAdminPresentation();
      } catch (error) {
        presentation = AdminPresentation.ENIGMA;
        renderAdminPresentation({ error: error?.message || "Admin Enigma verification failed." });
      }
    }
  };

  const onClick = async (event) => {
    const enter = event.target?.closest?.("[data-admin-auth-action='enter']");
    if (enter && eligibility?.eligible) {
      presentation = elevation ? AdminPresentation.WORKSPACE : AdminPresentation.CREDENTIALS;
      renderAdminPresentation();
      return;
    }

    const backDeveloper = event.target?.closest?.("[data-admin-auth-action='back-developer']");
    if (backDeveloper) {
      adminAttempt = null;
      presentation = AdminPresentation.DEVELOPER;
      renderDeveloperWorkspace();
      return;
    }

    const backCredentials = event.target?.closest?.("[data-admin-auth-action='back-credentials']");
    if (backCredentials) {
      adminAttempt = null;
      presentation = AdminPresentation.CREDENTIALS;
      renderAdminPresentation();
      return;
    }

    if (presentation === AdminPresentation.WORKSPACE && elevation) {
      const sectionTarget = event.target?.closest?.("[data-admin-workspace-section]");
      if (sectionTarget && Object.values(AdminWorkspaceSection).includes(sectionTarget.dataset.adminWorkspaceSection)) {
        activeSection = sectionTarget.dataset.adminWorkspaceSection;
        renderAdminPresentation();
        return;
      }
      const statusTarget = event.target?.closest?.("[data-admin-review-status]");
      if (statusTarget && Object.values(AdminReviewStatus).includes(statusTarget.dataset.adminReviewStatus)) {
        activeSection = AdminWorkspaceSection.REVIEWS;
        reviewStatus = statusTarget.dataset.adminReviewStatus;
        renderAdminPresentation();
        return;
      }
      if (event.target?.closest?.("[data-admin-review-decision]")) {
        event.preventDefault?.();
        return;
      }
    }

    const revoke = event.target?.closest?.("[data-admin-auth-action='revoke']");
    if (revoke) {
      const session = developerSession();
      const current = elevation;
      elevation = null;
      adminAttempt = null;
      presentation = AdminPresentation.DEVELOPER;
      resetWorkspaceState();
      clearExpiryTimer();
      renderDeveloperWorkspace();
      if (session?.sessionId && current?.elevationId) {
        try { await client.revokeAdminElevation(session.sessionId, current.elevationId); }
        catch { /* local elevation is still cleared */ }
      }
      return;
    }

    if (event.target?.closest?.("[data-auth-action='logout']")) clearAdminState();
  };

  const onHashChange = () => queueMicrotask(refresh);
  documentRef.addEventListener?.("submit", onSubmit);
  documentRef.addEventListener?.("click", onClick);
  windowRef?.addEventListener?.("hashchange", onHashChange);

  const Observer = windowRef?.MutationObserver || globalThis.MutationObserver;
  observer = Observer && outlet() ? new Observer(() => queueMicrotask(refresh)) : null;
  observe();
  void refresh();

  return Object.freeze({
    refresh,
    get elevation() { return elevation; },
    get adminAttempt() { return adminAttempt; },
    get presentation() { return presentation; },
    get activeSection() { return activeSection; },
    get reviewStatus() { return reviewStatus; },
    dispose() {
      clearExpiryTimer();
      observer?.disconnect?.();
      documentRef.removeEventListener?.("submit", onSubmit);
      documentRef.removeEventListener?.("click", onClick);
      windowRef?.removeEventListener?.("hashchange", onHashChange);
    },
  });
}
