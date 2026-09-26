import assert from "node:assert/strict";
import test from "node:test";

import { installAdminAuthenticationExperience } from "../../src/app/auth/admin-authentication-experience.js";

function fixture() {
  const listeners = new Map();
  let lastHtml = "";
  let boundaryPresent = false;
  const boundaryNode = {
    set outerHTML(value) { lastHtml = value; boundaryPresent = true; },
    remove() { boundaryPresent = false; lastHtml = ""; },
  };
  const workspace = {
    insertAdjacentHTML(_position, value) { lastHtml = value; boundaryPresent = true; },
  };
  const target = {};
  const documentRef = {
    querySelector(selector) {
      if (selector === "[data-role='admin-auth-boundary']") return boundaryPresent ? boundaryNode : null;
      if (selector === ".workspace-page") return workspace;
      if (selector === "[data-role='application-page']") return target;
      return null;
    },
    addEventListener(type, listener) { listeners.set(type, listener); },
    removeEventListener(type) { listeners.delete(type); },
  };
  const windowListeners = new Map();
  const windowRef = {
    addEventListener(type, listener) { windowListeners.set(type, listener); },
    removeEventListener(type) { windowListeners.delete(type); },
  };
  return { documentRef, windowRef, listeners, get html() { return lastHtml; } };
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

test("real elevation guards Admin Workspace sections and leave-Admin preserves Developer session", async () => {
  const originalFormData = globalThis.FormData;
  globalThis.FormData = class {
    constructor(form) { this.values = form.values; }
    get(name) { return this.values[name] ?? ""; }
  };
  try {
    const fx = fixture();
    const context = {
      session: {
        sessionId: "prod-session:1",
        identityType: "nexadevs_developer",
        runtime: "production",
      },
    };
    const calls = [];
    const client = {
      async adminEligibility(token) { calls.push(["eligibility", token]); return { eligible: true, boundEmailHint: "a***@example.com" }; },
      async startAdminElevation(token, input) { calls.push(["start", token, input]); return { attemptId: "admin-attempt:1", challenge: { words: ["ONE", "TWO", "SIX"], period: "Evening", wordLength: 3 } }; },
      async verifyAdminElevation(token, input) { calls.push(["verify", token, input]); return { elevation: { elevationId: "admin-elevation:1", adminOperatorId: "admin-operator:1", expiresAt: "2099-01-01T00:00:00Z", permissions: ["NEXILABS.ADMIN.ELEVATE"] } }; },
      async revokeAdminElevation(token, elevationId) { calls.push(["revoke", token, elevationId]); return { revoked: true }; },
    };
    const experience = installAdminAuthenticationExperience({
      documentRef: fx.documentRef,
      windowRef: fx.windowRef,
      authentication: { context },
      client,
    });
    await Promise.resolve();
    await Promise.resolve();
    assert.match(fx.html, /Admin Login/);

    await fx.listeners.get("submit")({
      target: submitTarget("elevate", { adminEmail: "admin@example.com", adminPassword: "separate-admin-password" }),
      preventDefault() {},
    });
    assert.match(fx.html, /Admin Enigma/);

    await fx.listeners.get("submit")({
      target: submitTarget("enigma", { response: "31SOMETHING" }),
      preventDefault() {},
    });
    assert.match(fx.html, /Admin Workspace/);
    assert.match(fx.html, /data-admin-elevated="true"/);

    await fx.listeners.get("click")({
      target: { closest: (selector) => selector === "[data-admin-workspace-section]" ? { dataset: { adminWorkspaceSection: "reviews" } } : null },
    });
    assert.match(fx.html, /data-admin-workspace-panel="reviews"/);

    await fx.listeners.get("click")({
      target: { closest: (selector) => selector === "[data-admin-review-status]" ? { dataset: { adminReviewStatus: "REJECTED" } } : null },
    });
    assert.match(fx.html, /data-admin-review-status="REJECTED" aria-selected="true"/);

    const callCountBeforeDecision = calls.length;
    await fx.listeners.get("click")({
      target: { closest: (selector) => selector === "[data-admin-review-decision]" ? { dataset: { adminReviewDecision: "approve" } } : null },
      preventDefault() {},
    });
    assert.equal(calls.length, callCountBeforeDecision, "deferred Reviews UI must not call a fake decision authority");

    await fx.listeners.get("click")({
      target: {
        closest(selector) {
          if (selector === "[data-admin-auth-action='revoke']") return {};
          return null;
        },
      },
    });
    assert.equal(context.session.sessionId, "prod-session:1");
    assert.match(fx.html, /Admin Login/);
    assert.ok(calls.some(([kind]) => kind === "revoke"));
    experience.dispose();
  } finally {
    globalThis.FormData = originalFormData;
  }
});
