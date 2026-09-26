import test from "node:test";
import assert from "node:assert/strict";
import { registerServiceWorker, ServiceWorkerStatus } from "../src/pwa/service-worker-registration.js";

function statusDocument() {
  const node = { textContent: "", dataset: {} };
  return { node, querySelectorAll: () => [node] };
}

test("unsupported browsers return an explicit non-failing receipt", async () => {
  const documentRef = statusDocument();
  const receipt = await registerServiceWorker({ navigatorRef: {}, documentRef });
  assert.equal(receipt.supported, false);
  assert.equal(receipt.status, ServiceWorkerStatus.UNSUPPORTED);
  assert.equal(documentRef.node.dataset.pwaStatus, "UNSUPPORTED");
});

test("registration uses local scope, bypasses stale HTTP cache and exposes update controls", async () => {
  const calls = [];
  const waiting = { messages: [], postMessage(message) { this.messages.push(message); } };
  const registration = {
    waiting,
    addEventListener() {},
    async update() { calls.push("update"); }
  };
  const serviceWorker = {
    controller: {},
    async register(url, options) { calls.push([url, options]); return registration; },
    addEventListener() {}
  };
  const receipt = await registerServiceWorker({ navigatorRef: { serviceWorker }, documentRef: statusDocument() });
  assert.deepEqual(calls[0], ["./sw.js", { scope: "./", updateViaCache: "none" }]);
  assert.equal(receipt.status, ServiceWorkerStatus.UPDATE_READY);
  assert.equal(receipt.activateUpdate(), true);
  assert.deepEqual(waiting.messages, [{ type: "SKIP_WAITING" }]);
  assert.equal(await receipt.checkForUpdate(), true);
});

test("registration failure is contained and reported", async () => {
  const failure = new Error("offline");
  const documentRef = statusDocument();
  const receipt = await registerServiceWorker({
    navigatorRef: { serviceWorker: { register: async () => { throw failure; } } },
    documentRef
  });
  assert.equal(receipt.status, ServiceWorkerStatus.FAILED);
  assert.equal(receipt.error, failure);
  assert.equal(documentRef.node.dataset.pwaStatus, "FAILED");
});


function eventTarget(initial = {}) {
  const listeners = new Map();
  return Object.assign(initial, {
    addEventListener(type, listener) {
      const set = listeners.get(type) || new Set();
      set.add(listener);
      listeners.set(type, set);
    },
    removeEventListener(type, listener) {
      listeners.get(type)?.delete(listener);
    },
    dispatch(type, event = {}) {
      for (const listener of listeners.get(type) || []) listener(event);
    },
  });
}

test("Bundle 12.0E automatically activates a waiting complete shell and exposes its generation", async () => {
  const waiting = { messages: [], postMessage(message) { this.messages.push(message); } };
  const registration = eventTarget({ waiting, installing: null, async update() {} });
  const serviceWorker = eventTarget({
    controller: {},
    async register() { return registration; },
  });
  const documentRef = eventTarget(statusDocument());
  documentRef.documentElement = { dataset: {} };
  documentRef.visibilityState = "visible";
  const windowRef = eventTarget({ dispatchEvent() {} });

  const receipt = await registerServiceWorker({ navigatorRef: { serviceWorker }, documentRef, windowRef });
  assert.equal(receipt.generation, "nexilabs-shell-v17");
  assert.equal(documentRef.documentElement.dataset.shellGeneration, "nexilabs-shell-v17");
  assert.deepEqual(waiting.messages, [{ type: "SKIP_WAITING" }]);
  receipt.dispose();
});

test("Bundle 12.0E foreground update discovery is opportunistic and keeps the cached app usable on failure", async () => {
  let updateCalls = 0;
  const registration = eventTarget({
    waiting: null,
    installing: null,
    async update() { updateCalls += 1; throw new Error("offline"); },
  });
  const serviceWorker = eventTarget({ controller: {}, async register() { return registration; } });
  const documentRef = eventTarget(statusDocument());
  documentRef.documentElement = { dataset: {} };
  documentRef.visibilityState = "visible";
  const windowRef = eventTarget({ dispatchEvent() {} });

  const receipt = await registerServiceWorker({ navigatorRef: { serviceWorker }, documentRef, windowRef });
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.equal(receipt.status, ServiceWorkerStatus.REGISTERED);
  assert.ok(updateCalls >= 1);
  assert.equal(await receipt.checkForUpdate(), false);
  receipt.dispose();
});

test("Bundle 12.0E foreground listeners are disposable and do not reload from controllerchange", async () => {
  const registration = eventTarget({ waiting: null, installing: null, async update() {} });
  const serviceWorker = eventTarget({ controller: {}, async register() { return registration; } });
  const documentRef = eventTarget(statusDocument());
  documentRef.documentElement = { dataset: {} };
  documentRef.visibilityState = "visible";
  let reloads = 0;
  const windowRef = eventTarget({ dispatchEvent() {}, location: { reload() { reloads += 1; } } });

  const receipt = await registerServiceWorker({ navigatorRef: { serviceWorker }, documentRef, windowRef });
  serviceWorker.dispatch("controllerchange");
  assert.equal(receipt.status, ServiceWorkerStatus.ACTIVATED);
  assert.equal(reloads, 0);
  receipt.dispose();
});


test("P006.UI.16 browser registration generation is derived from the current cache policy", async () => {
  const { PWA_SHELL_GENERATION } = await import("../src/pwa/service-worker-registration.js");
  const { PWA_CACHE_VERSION } = await import("../src/pwa/cache-policy.js");
  assert.equal(PWA_SHELL_GENERATION, PWA_CACHE_VERSION);
  assert.equal(PWA_SHELL_GENERATION, "nexilabs-shell-v17");
});

test("late-mounted footer replays the already-settled Service Worker status", async () => {
  let statusNodes = [];
  const registration = eventTarget({ waiting: null, installing: null, async update() {} });
  const serviceWorker = eventTarget({
    controller: {},
    async register() { return registration; },
  });
  const documentRef = eventTarget({
    documentElement: { dataset: {} },
    visibilityState: "visible",
    querySelectorAll() { return statusNodes; },
  });
  const windowRef = eventTarget({ dispatchEvent() {} });

  const receipt = await registerServiceWorker({
    navigatorRef: { serviceWorker },
    documentRef,
    windowRef,
  });

  assert.equal(receipt.status, ServiceWorkerStatus.REGISTERED);

  const footerStatus = {
    textContent: "registering",
    dataset: { pwaStatus: "REGISTERING" },
  };
  statusNodes = [footerStatus];

  documentRef.dispatch("nexilabs:shell-partial-loaded");

  assert.equal(footerStatus.dataset.pwaStatus, ServiceWorkerStatus.REGISTERED);
  assert.equal(footerStatus.textContent, "registered");
  receipt.dispose();
});
