/** P006.UI.10.4 — Conditional Admin elevation and guarded Admin Workspace. */
import { createProductionAuthClient } from "./production-auth-client-p006-ui-10-4.js";
import { adminEnigmaMarkup, adminLoginMarkup } from "../../ui/pages/admin-login.js";
import { adminWorkspaceMarkup, AdminWorkspaceSection } from "../../ui/pages/admin-workspace.js";
import { AdminReviewStatus } from "../admin/admin-review-view-model.js";

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
  let activeSection = AdminWorkspaceSection.OVERVIEW;
  let reviewStatus = AdminReviewStatus.PENDING;
  let refreshGeneration = 0;
  let observer = null;
  let expiryTimer = null;

  const boundary = () => documentRef.querySelector?.("[data-role='admin-auth-boundary']");
  const workspace = () => documentRef.querySelector?.(".workspace-page");
  const target = documentRef.querySelector?.("[data-role='application-page']");

  const observe = () => observer?.observe?.(target, { childList: true, subtree: true });
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
  const resetAdminPresentationState = () => {
    activeSection = AdminWorkspaceSection.OVERVIEW;
    reviewStatus = AdminReviewStatus.PENDING;
  };
  const removeBoundary = () => mutatePresentation(() => boundary()?.remove?.());

  const scheduleExpiry = () => {
    clearExpiryTimer();
    if (!elevation?.expiresAt || !windowRef?.setTimeout) return;
    const delay = Math.max(0, Date.parse(elevation.expiresAt) - Date.now());
    expiryTimer = windowRef.setTimeout(async () => {
      const session = authentication.context.session;
      const current = elevation;
      elevation = null;
      adminAttempt = null;
      resetAdminPresentationState();
      renderBoundary();
      if (session?.sessionId && current?.elevationId) {
        try { await client.revokeAdminElevation(session.sessionId, current.elevationId); } catch { /* expiry is still local */ }
      }
    }, Math.min(delay, 2_147_000_000));
  };

  const renderBoundary = ({ error = "" } = {}) => {
    const root = workspace();
    if (!root || !eligibility?.eligible) {
      clearExpiryTimer();
      removeBoundary();
      return;
    }
    const markup = elevation
      ? adminWorkspaceMarkup({ elevation, activeSection, reviewStatus })
      : adminAttempt
        ? adminEnigmaMarkup({ challenge: adminAttempt.challenge, error })
        : adminLoginMarkup({ eligibility, error });
    mutatePresentation(() => {
      const existing = boundary();
      if (existing) existing.outerHTML = markup;
      else root.insertAdjacentHTML?.("beforeend", markup);
    });
    if (elevation) scheduleExpiry();
    else clearExpiryTimer();
  };

  const refresh = async () => {
    const generation = ++refreshGeneration;
    const session = authentication.context.session;
    if (!session?.sessionId || session.identityType !== "nexadevs_developer" || session.runtime !== "production") {
      eligibility = null;
      adminAttempt = null;
      elevation = null;
      resetAdminPresentationState();
      clearExpiryTimer();
      removeBoundary();
      return null;
    }
    try {
      const payload = await client.adminEligibility(session.sessionId);
      if (generation !== refreshGeneration) return null;
      eligibility = payload;
      if (!eligibility.eligible) {
        adminAttempt = null;
        elevation = null;
        resetAdminPresentationState();
      }
      renderBoundary();
      return eligibility;
    } catch {
      if (generation !== refreshGeneration) return null;
      eligibility = null;
      adminAttempt = null;
      elevation = null;
      resetAdminPresentationState();
      clearExpiryTimer();
      removeBoundary();
      return null;
    }
  };

  const onSubmit = async (event) => {
    const credentialForm = event.target?.closest?.("[data-admin-auth-form='elevate']");
    const enigmaForm = event.target?.closest?.("[data-admin-auth-form='enigma']");
    const reviewForm = event.target?.closest?.("[data-admin-review-decision-form]");
    if (reviewForm) {
      event.preventDefault();
      return; // Review persistence authority is deliberately deferred.
    }
    if (!credentialForm && !enigmaForm) return;
    event.preventDefault();
    const session = authentication.context.session;
    if (!session?.sessionId) return;

    if (credentialForm) {
      try {
        const payload = await client.startAdminElevation(session.sessionId, {
          adminEmail: formValue(credentialForm, "adminEmail"),
          adminPassword: formValue(credentialForm, "adminPassword"),
        });
        adminAttempt = { attemptId: payload.attemptId, challenge: payload.challenge };
        elevation = null;
        resetAdminPresentationState();
        renderBoundary();
      } catch (error) {
        adminAttempt = null;
        elevation = null;
        resetAdminPresentationState();
        renderBoundary({ error: error?.message || "Admin login failed." });
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
        resetAdminPresentationState();
        renderBoundary();
      } catch (error) {
        renderBoundary({ error: error?.message || "Admin Enigma verification failed." });
      }
    }
  };

  const onClick = async (event) => {
    if (elevation) {
      const sectionTarget = event.target?.closest?.("[data-admin-workspace-section]");
      if (sectionTarget && Object.values(AdminWorkspaceSection).includes(sectionTarget.dataset.adminWorkspaceSection)) {
        activeSection = sectionTarget.dataset.adminWorkspaceSection;
        renderBoundary();
        return;
      }
      const statusTarget = event.target?.closest?.("[data-admin-review-status]");
      if (statusTarget && Object.values(AdminReviewStatus).includes(statusTarget.dataset.adminReviewStatus)) {
        activeSection = AdminWorkspaceSection.REVIEWS;
        reviewStatus = statusTarget.dataset.adminReviewStatus;
        renderBoundary();
        return;
      }
      if (event.target?.closest?.("[data-admin-review-decision]")) {
        event.preventDefault?.();
        return; // Never fabricate a persisted decision.
      }
    }

    const revoke = event.target?.closest?.("[data-admin-auth-action='revoke']");
    if (revoke) {
      const session = authentication.context.session;
      const current = elevation;
      elevation = null;
      adminAttempt = null;
      resetAdminPresentationState();
      clearExpiryTimer();
      renderBoundary();
      if (session?.sessionId && current?.elevationId) {
        try { await client.revokeAdminElevation(session.sessionId, current.elevationId); } catch { /* local elevation is still cleared */ }
      }
      return;
    }
    if (event.target?.closest?.("[data-auth-action='logout']")) {
      eligibility = null;
      adminAttempt = null;
      elevation = null;
      resetAdminPresentationState();
      clearExpiryTimer();
      removeBoundary();
    }
  };

  const onHashChange = () => queueMicrotask(refresh);
  documentRef.addEventListener?.("submit", onSubmit);
  documentRef.addEventListener?.("click", onClick);
  windowRef?.addEventListener?.("hashchange", onHashChange);

  const Observer = windowRef?.MutationObserver || globalThis.MutationObserver;
  observer = Observer && target
    ? new Observer(() => queueMicrotask(refresh))
    : null;
  observe();
  void refresh();

  return Object.freeze({
    refresh,
    get elevation() { return elevation; },
    get adminAttempt() { return adminAttempt; },
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
