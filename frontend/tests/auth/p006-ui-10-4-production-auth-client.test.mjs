import assert from "node:assert/strict";
import test from "node:test";

import {
  createProductionAuthClient,
  defaultProductionAuthBase,
} from "../../src/app/auth/production-auth-client-p006-ui-10-4.js";

function response(payload, status = 200) {
  return { ok: status >= 200 && status < 300, status, json: async () => payload };
}

test("deployed HTTPS PWA uses same-origin Production-auth transport with no public raw port", () => {
  assert.equal(defaultProductionAuthBase({ location: { protocol: "https:", hostname: "nexilabs.nexaecosystem.com" } }), "");
});

test("bounded localhost HTTP qualification retains the locked direct 8767 transport", () => {
  assert.equal(defaultProductionAuthBase({ location: { protocol: "http:", hostname: "127.0.0.1" } }), "http://127.0.0.1:8767");
});

test("same-origin Developer request stays under /auth and never embeds the browser hostname", async () => {
  const calls = [];
  const client = createProductionAuthClient({
    windowRef: { location: { protocol: "https:", hostname: "nexilabs.nexaecosystem.com" } },
    fetchRef: async (url, options) => { calls.push({ url, options }); return response({ ok: true, attemptId: "a", challenge: {} }); },
  });
  await client.startDeveloper({ username: "dev", password: "secret", runtime: "production" });
  assert.equal(calls[0].url, "/auth/developer/start");
  assert.equal(calls[0].options.cache, "no-store");
  assert.equal(calls[0].options.credentials, "same-origin");
});

test("same-origin Admin methods use canonical /auth/admin namespace and bearer header", async () => {
  const calls = [];
  const client = createProductionAuthClient({
    baseUrl: "",
    fetchRef: async (url, options) => { calls.push({ url, options }); return response({ ok: true, eligible: true }); },
  });
  await client.adminEligibility("prod-session:1");
  assert.equal(calls[0].url, "/auth/admin/eligibility");
  assert.equal(calls[0].options.headers.Authorization, "Bearer prod-session:1");
  assert.doesNotMatch(calls[0].url, /8767/);
  assert.match(calls[0].url, /^\/auth\/admin\/eligibility$/);
});

test("explicit bounded locked-authority base keeps legacy /admin route for local compatibility", async () => {
  const calls = [];
  const client = createProductionAuthClient({
    baseUrl: "http://127.0.0.1:8767",
    fetchRef: async (url, options) => { calls.push({ url, options }); return response({ ok: true, attemptId: "a", challenge: {} }); },
  });
  await client.startAdminElevation("prod-session:1", { adminEmail: "a@example.com", adminPassword: "different-secret" });
  assert.equal(calls[0].url, "http://127.0.0.1:8767/admin/elevate");
});
