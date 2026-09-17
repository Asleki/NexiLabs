/** P006.UI.10.3 R2 — Conditional Admin elevation inside an authenticated Production Developer session. */
import { createProductionAuthClient } from "./production-auth-client.js";
import { adminElevatedMarkup, adminEnigmaMarkup, adminLoginMarkup } from "../../ui/pages/admin-login.js";

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
      ? adminElevatedMarkup({ elevation })
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
      }
      renderBoundary();
      return eligibility;
    } catch {
      if (generation !== refreshGeneration) return null;
      eligibility = null;
      adminAttempt = null;
      elevation = null;
      clearExpiryTimer();
      removeBoundary();
      return null;
    }
  };

  const onSubmit = async (event) => {
    const credentialForm = event.target?.closest?.("[data-admin-auth-form='elevate']");
    const enigmaForm = event.target?.closest?.("[data-admin-auth-form='enigma']");
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
        renderBoundary();
      } catch (error) {
        adminAttempt = null;
        elevation = null;
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
        renderBoundary();
      } catch (error) {
        renderBoundary({ error: error?.message || "Admin Enigma verification failed." });
      }
    }
  };

  const onClick = async (event) => {
    const revoke = event.target?.closest?.("[data-admin-auth-action='revoke']");
    if (revoke) {
      const session = authentication.context.session;
      const current = elevation;
      elevation = null;
      adminAttempt = null;
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
    dispose() {
      clearExpiryTimer();
      observer?.disconnect?.();
      documentRef.removeEventListener?.("submit", onSubmit);
      documentRef.removeEventListener?.("click", onClick);
      windowRef?.removeEventListener?.("hashchange", onHashChange);
    },
  });
}
