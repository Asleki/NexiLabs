import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import vm from "node:vm";

const REPO_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const HISTORICAL_WORKER = resolve(REPO_ROOT, "frontend/sw.js");
const PTB11_WORKER = resolve(
  REPO_ROOT,
  "infrastructure/deployment/config/nexilabs-ptb11-sw.js"
);
const source = readFileSync(PTB11_WORKER, "utf8");
const historicalSource = readFileSync(HISTORICAL_WORKER, "utf8");

function loadWorker({ cacheEntries = [] } = {}) {
  const listeners = new Map();
  const deleted = [];
  const cache = {
    addAll: async () => undefined,
    keys: async () => cacheEntries,
    delete: async (request) => {
      deleted.push(request.url ?? request);
      return true;
    },
    put: async () => undefined,
  };
  const state = {
    cacheMatchCalls: [],
    fetchCalls: [],
    deleted,
    claimed: 0,
  };
  const context = {
    URL,
    AbortController,
    setTimeout,
    clearTimeout,
    console,
    fetch: async (request, options) => {
      state.fetchCalls.push({ request, options });
      return { source: "network", status: 200, type: "basic", clone() { return this; } };
    },
    caches: {
      keys: async () => ["nexilabs-shell-v17"],
      open: async () => cache,
      delete: async () => true,
      match: async (request) => {
        state.cacheMatchCalls.push(request);
        return { source: "cache", request };
      },
    },
    self: {
      location: { origin: "https://nexilabs.example" },
      addEventListener(type, handler) { listeners.set(type, handler); },
      skipWaiting: async () => undefined,
      clients: {
        claim: async () => { state.claimed += 1; },
        matchAll: async () => [],
      },
    },
  };
  vm.createContext(context);
  vm.runInContext(source, context, { filename: "nexilabs-ptb11-sw.js" });
  return { listeners, state };
}

async function dispatchFetch(listener, request) {
  let responsePromise;
  listener({
    request,
    respondWith(value) { responsePromise = Promise.resolve(value); },
  });
  return responsePromise ? responsePromise : undefined;
}

test("PTB.11 preserves the historical frontend worker as predecessor evidence", () => {
  assert.doesNotMatch(historicalSource, /LIVE_AUTHORITY_PATH_PREFIXES/);
  assert.match(historicalSource, /CACHE_NAME = "nexilabs-shell-v17"/);
  assert.match(source, /LIVE_AUTHORITY_PATH_PREFIXES/);
  assert.notEqual(source, historicalSource);
});

test("PTB.11 classifies oauth2, auth and api/v1 as live authority", () => {
  assert.match(source, /LIVE_AUTHORITY_PATH_PREFIXES/);
  for (const path of ["/oauth2", "/auth", "/api/v1"]) {
    assert.ok(source.includes(`"${path}"`), path);
  }
  assert.match(source, /isLiveAuthorityPath\(url\.pathname\)/);
  assert.match(source, /fetch\(request, \{ cache: "no-store" \}\)/);
});

test("PTB.11 live-authority GETs bypass CacheStorage reads and writes", async () => {
  for (const path of [
    "/oauth2/auth",
    "/auth/session",
    "/api/v1/nngla-map/features",
  ]) {
    const { listeners, state } = loadWorker();
    const response = await dispatchFetch(listeners.get("fetch"), {
      method: "GET",
      mode: "cors",
      url: `https://nexilabs.example${path}`,
    });
    assert.equal(response.status, 200, path);
    assert.equal(state.cacheMatchCalls.length, 0, path);
    assert.equal(state.fetchCalls.length, 1, path);
    assert.equal(state.fetchCalls[0].options.cache, "no-store", path);
  }
});

test("PTB.11 live-authority navigation never falls back to offline index", async () => {
  const { listeners, state } = loadWorker();
  await dispatchFetch(listeners.get("fetch"), {
    method: "GET",
    mode: "navigate",
    url: "https://nexilabs.example/auth/login",
  });
  assert.equal(state.cacheMatchCalls.length, 0);
  assert.equal(state.fetchCalls.length, 1);
  assert.equal(state.fetchCalls[0].options.cache, "no-store");
});

test("PTB.11 ordinary application assets retain cache-first offline behavior", async () => {
  const { listeners, state } = loadWorker();
  const response = await dispatchFetch(listeners.get("fetch"), {
    method: "GET",
    mode: "cors",
    url: "https://nexilabs.example/styles/app.css",
  });
  assert.equal(response.source, "cache");
  assert.equal(state.cacheMatchCalls.length, 1);
  assert.equal(state.fetchCalls.length, 0);
});

test("PTB.11 activation removes stale authority entries without purging shell assets", async () => {
  const cacheEntries = [
    { url: "https://nexilabs.example/api/v1/nngla-map/features" },
    { url: "https://nexilabs.example/auth/session" },
    { url: "https://nexilabs.example/oauth2/auth" },
    { url: "https://nexilabs.example/styles/app.css" },
    { url: "https://nexilabs.example/public/geography/novegeo/world-boundary/v002/standard.geojson" },
  ];
  const { listeners, state } = loadWorker({ cacheEntries });
  let activation;
  listeners.get("activate")({ waitUntil(value) { activation = Promise.resolve(value); } });
  await activation;
  assert.deepEqual(
    state.deleted.sort(),
    [
      "https://nexilabs.example/api/v1/nngla-map/features",
      "https://nexilabs.example/auth/session",
      "https://nexilabs.example/oauth2/auth",
    ].sort()
  );
  assert.equal(state.claimed, 1);
});

test("PTB.11 edge worker preserves v17 shell inventory and offline fallback", () => {
  assert.match(source, /CACHE_NAME = "nexilabs-shell-v17"/);
  assert.match(source, /await cache\.addAll\(APP_SHELL\)/);
  assert.match(source, /caches\.match\(OFFLINE_URL\)/);
  assert.match(source, /request\.mode === "navigate"/);
  assert.match(source, /\.\/src\/ui\/pages\/simulation-workspace\.js/);
  assert.match(source, /\.\/src\/app\/features\/novegeo-feature-runtime\.js/);
});


test("P006.UI.10.4 frontend access integration has an explicit same-generation refresh", () => {
  assert.match(source, /nexilabs-refresh-p006-ui-10-4-r2/);
  assert.match(source, /FRONTEND_ACCESS_INTEGRATION_PATHS/);

  for (const path of [
    "/src/app/account/account-enrollment-experience.js",
    "/src/app/admin/admin-review-view-model.js",
    "/src/app/auth/admin-authentication-experience.js",
    "/src/app/auth/production-auth-client-p006-ui-10-4.js",
    "/src/app/auth/runtime-auth-client.js",
    "/src/ui/pages/admin-workspace.js",
    "/src/ui/pages/developer-account-enrollment-p006-ui-10-4.js",
  ]) {
    assert.ok(source.includes(`"${path}"`), path);
  }
});

test("P006.UI.10.4 frontend access modules prefer live network over stale CacheStorage", async () => {
  const { listeners, state } = loadWorker();

  const response = await dispatchFetch(listeners.get("fetch"), {
    method: "GET",
    mode: "cors",
    url: "https://nexilabs.example/src/app/auth/runtime-auth-client.js",
  });

  assert.equal(response.source, "network");
  assert.equal(state.fetchCalls.length, 1);
  assert.equal(state.fetchCalls[0].options.cache, "no-store");
  assert.equal(state.cacheMatchCalls.length, 0);
});
