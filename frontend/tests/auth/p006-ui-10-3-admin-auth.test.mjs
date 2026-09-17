import assert from "node:assert/strict";
import test from "node:test";

import { adminElevatedMarkup, adminEnigmaMarkup, adminLoginMarkup } from "../../src/ui/pages/admin-login.js";
import { createProductionAuthClient, defaultProductionAuthBase } from "../../src/app/auth/production-auth-client.js";


test("Admin presentation is conditional elevation inside Production and requires separate Admin password", () => {
  const markup = adminLoginMarkup({ eligibility: { boundEmailHint: "a***z@example.com" } });
  assert.match(markup, /Admin elevation/);
  assert.match(markup, /separate Admin password/i);
  assert.match(markup, /data-admin-auth-form="elevate"/);
  assert.doesNotMatch(markup, /Admin runtime/i);
});


test("Admin Enigma presentation reuses governed challenge while requiring Admin bootstrap secret", () => {
  const markup = adminEnigmaMarkup({ challenge: {
    words: ["PATCH", "BATCH", "MATCH"],
    period: "Evening",
    wordLength: 5,
  }});
  assert.match(markup, /Admin Enigma/);
  assert.match(markup, /PATCH/);
  assert.match(markup, /BATCH/);
  assert.match(markup, /MATCH/);
  assert.match(markup, /bootstrap Enigma secret/);
  assert.match(markup, /data-admin-auth-form="enigma"/);
});


test("elevated presentation shows exact permissions and expiry", () => {
  const markup = adminElevatedMarkup({ elevation: {
    adminOperatorId: "admin-operator:1",
    expiresAt: "2026-09-15T20:00:00+00:00",
    permissions: ["NEXILABS.ADMIN.ELEVATE", "NEXILABS.AUDIT.READ"],
  }});
  assert.match(markup, /NEXILABS.ADMIN.ELEVATE/);
  assert.match(markup, /volatile browser context/);
});


test("production auth base uses dedicated loopback port", () => {
  assert.equal(defaultProductionAuthBase({ location: { hostname: "127.0.0.1" } }), "http://127.0.0.1:8767");
});


test("Admin credentials start elevation Enigma and bearer token is not persisted", async () => {
  const calls = [];
  const fetchRef = async (url, options) => {
    calls.push({ url, options });
    return { ok: true, json: async () => ({ ok: true, attemptId: "a:1", challenge: { words: [] } }) };
  };
  const client = createProductionAuthClient({ fetchRef, baseUrl: "http://127.0.0.1:8767" });
  const payload = await client.startAdminElevation("prod-session:1", { adminEmail: "a@example.com", adminPassword: "secret" });
  assert.equal(payload.attemptId, "a:1");
  assert.equal(calls[0].url, "http://127.0.0.1:8767/admin/elevate");
  assert.equal(calls[0].options.headers.Authorization, "Bearer prod-session:1");
  assert.match(calls[0].options.body, /"adminEmail":"a@example.com"/);
});


test("Admin Enigma verification is a distinct second request", async () => {
  const calls = [];
  const fetchRef = async (url, options) => {
    calls.push({ url, options });
    return { ok: true, json: async () => ({ ok: true, elevation: { elevationId: "e:1" } }) };
  };
  const client = createProductionAuthClient({ fetchRef, baseUrl: "http://127.0.0.1:8767" });
  const payload = await client.verifyAdminElevation("prod-session:1", { attemptId: "a:1", response: "31BLUECIPHER" });
  assert.equal(payload.elevation.elevationId, "e:1");
  assert.equal(calls[0].url, "http://127.0.0.1:8767/admin/elevate/enigma");
  assert.equal(calls[0].options.headers.Authorization, "Bearer prod-session:1");
  assert.match(calls[0].options.body, /"attemptId":"a:1"/);
});
