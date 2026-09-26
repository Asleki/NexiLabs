import assert from "node:assert/strict";
import test from "node:test";

import {
  AdminPresentation,
  installAdminAuthenticationExperience,
} from "../../src/app/auth/admin-authentication-experience.js";

function fixture() {
  const listeners = new Map();
  const windowListeners = new Map();
  let pageHtml = "Production Developer Workspace";
  const adminActions = { innerHTML: "" };
  const target = {
    get innerHTML() { return pageHtml; },
    set innerHTML(value) { pageHtml = value; },
  };
  const root = { dataset: { applicationRoute: "production-developer" } };
  const documentRef = {
    querySelector(selector) {
      if (selector === "[data-role='application-page']") return target;
      if (selector === "[data-role='developer-admin-actions']") return adminActions;
      if (selector === "#nexilabs-app") return root;
      return null;
    },
    addEventListener(type, listener) { listeners.set(type, listener); },
    removeEventListener(type) { listeners.delete(type); },
  };
  const windowRef = {
    addEventListener(type, listener) { windowListeners.set(type, listener); },
    removeEventListener(type) { windowListeners.delete(type); },
  };
  return {
    documentRef,
    windowRef,
    listeners,
    root,
    adminActions,
    get html() { return pageHtml; },
    renderDeveloper() {
      pageHtml = "Production Developer Workspace";
      adminActions.innerHTML = "";
    },
  };
}

function submitTarget(formKind, values) {
  const form = { values };
  return {
    closest(selector) {
      if (formKind === "elevate" && selector === "[data-admin-auth-form='elevate']") return form;
      if (formKind === "enigma" && selector === "[data-admin-auth-form='enigma']") return form;
      return null;
    },
  };
}

function clickTarget(matches) {
  return { closest(selector) { return matches[selector] ?? null; } };
}

test("eligible Developer gets an Admin Access action without appended Admin forms", async () => {
  const fx = fixture();
  const context = { session: { sessionId: "prod-session:1", identityType: "nexadevs_developer", runtime: "production" } };
  const client = { async adminEligibility() { return { eligible: true, boundEmailHint: "a***@example.com" }; } };
  const experience = installAdminAuthenticationExperience({
    documentRef: fx.documentRef,
    windowRef: fx.windowRef,
    authentication: { context, render() { fx.renderDeveloper(); return true; } },
    client,
  });
  await Promise.resolve();
  await Promise.resolve();
  assert.equal(experience.presentation, AdminPresentation.DEVELOPER);
  assert.match(fx.html, /Production Developer Workspace/);
  assert.doesNotMatch(fx.html, /Admin sign in/);
  assert.match(fx.adminActions.innerHTML, /Admin Access/);
  experience.dispose();
});

test("Admin credentials, Enigma and Workspace replace the Developer page instead of appending below it", async () => {
  const originalFormData = globalThis.FormData;
  globalThis.FormData = class {
    constructor(form) { this.values = form.values; }
    get(name) { return this.values[name] ?? ""; }
  };
  try {
    const fx = fixture();
    const context = { session: { sessionId: "prod-session:1", identityType: "nexadevs_developer", runtime: "production" } };
    const calls = [];
    const client = {
      async adminEligibility(token) {
        calls.push(["eligibility", token]);
        return { eligible: true, boundEmailHint: "a***@example.com" };
      },
      async startAdminElevation(token, input) {
        calls.push(["start", token, input]);
        return { attemptId: "admin-attempt:1", challenge: { words: ["TEST", "REST", "BEST"], period: "Morning", wordLength: 4 } };
      },
      async verifyAdminElevation(token, input) {
        calls.push(["verify", token, input]);
        return { elevation: { elevationId: "admin-elevation:1", adminOperatorId: "admin-operator:1", expiresAt: "2099-01-01T00:00:00Z", permissions: ["NEXILABS.ADMIN.ELEVATE"] } };
      },
      async revokeAdminElevation(token, elevationId) {
        calls.push(["revoke", token, elevationId]);
        return { revoked: true };
      },
    };
    const experience = installAdminAuthenticationExperience({
      documentRef: fx.documentRef,
      windowRef: fx.windowRef,
      authentication: { context, render() { fx.renderDeveloper(); return true; } },
      client,
    });
    await Promise.resolve();
    await Promise.resolve();

    await fx.listeners.get("click")({ target: clickTarget({ "[data-admin-auth-action='enter']": {} }) });
    assert.equal(experience.presentation, AdminPresentation.CREDENTIALS);
    assert.match(fx.html, /Admin sign in/);
    assert.doesNotMatch(fx.html, /Production Developer Workspace/);

    await fx.listeners.get("submit")({
      target: submitTarget("elevate", { adminEmail: "admin@example.com", adminPassword: "separate-admin-password" }),
      preventDefault() {},
    });
    assert.equal(experience.presentation, AdminPresentation.ENIGMA);
    assert.match(fx.html, /Admin Enigma/);
    assert.match(fx.html, /class="enigma-challenge admin-enigma-challenge"/);
    assert.match(fx.html, /TEST/);
    assert.match(fx.html, /REST/);
    assert.match(fx.html, /BEST/);
    assert.doesNotMatch(fx.html, /Production Developer Workspace/);

    await fx.listeners.get("submit")({ target: submitTarget("enigma", { response: "31SOMETHING" }), preventDefault() {} });
    assert.equal(experience.presentation, AdminPresentation.WORKSPACE);
    assert.match(fx.html, /Admin Workspace/);
    assert.match(fx.html, /data-admin-elevated="true"/);
    assert.doesNotMatch(fx.html, /Production Developer Workspace/);

    await fx.listeners.get("click")({ target: clickTarget({ "[data-admin-workspace-section]": { dataset: { adminWorkspaceSection: "reviews" } } }) });
    assert.match(fx.html, /data-admin-workspace-panel="reviews"/);

    await fx.listeners.get("click")({ target: clickTarget({ "[data-admin-review-status]": { dataset: { adminReviewStatus: "REJECTED" } } }) });
    assert.match(fx.html, /data-admin-review-status="REJECTED" aria-selected="true"/);

    const callCountBeforeDecision = calls.length;
    await fx.listeners.get("click")({
      target: clickTarget({ "[data-admin-review-decision]": { dataset: { adminReviewDecision: "approve" } } }),
      preventDefault() {},
    });
    assert.equal(calls.length, callCountBeforeDecision, "deferred Reviews UI must not call a fake decision authority");

    await fx.listeners.get("click")({ target: clickTarget({ "[data-admin-auth-action='revoke']": {} }) });
    assert.equal(context.session.sessionId, "prod-session:1");
    assert.equal(experience.presentation, AdminPresentation.DEVELOPER);
    assert.match(fx.html, /Production Developer Workspace/);
    assert.match(fx.adminActions.innerHTML, /Admin Access/);
    assert.ok(calls.some(([kind]) => kind === "revoke"));
    experience.dispose();
  } finally {
    globalThis.FormData = originalFormData;
  }
});

test("Admin credentials can return to Developer Workspace without ending the Developer session", async () => {
  const fx = fixture();
  const context = { session: { sessionId: "prod-session:1", identityType: "nexadevs_developer", runtime: "production" } };
  const client = { async adminEligibility() { return { eligible: true, boundEmailHint: "a***@example.com" }; } };
  const experience = installAdminAuthenticationExperience({
    documentRef: fx.documentRef,
    windowRef: fx.windowRef,
    authentication: { context, render() { fx.renderDeveloper(); return true; } },
    client,
  });
  await Promise.resolve();
  await Promise.resolve();
  await fx.listeners.get("click")({ target: clickTarget({ "[data-admin-auth-action='enter']": {} }) });
  assert.match(fx.html, /Admin sign in/);
  await fx.listeners.get("click")({ target: clickTarget({ "[data-admin-auth-action='back-developer']": {} }) });
  assert.equal(context.session.sessionId, "prod-session:1");
  assert.match(fx.html, /Production Developer Workspace/);
  assert.match(fx.adminActions.innerHTML, /Admin Access/);
  experience.dispose();
});
