/** P003.2/P003.4 / Bundle 12.0E / P006.UI.16 — Browser-side service worker registration and generation recovery boundary. */
import { PWA_CACHE_VERSION } from "./cache-policy.js";
export const ServiceWorkerStatus = Object.freeze({
  UNSUPPORTED: "UNSUPPORTED",
  REGISTERING: "REGISTERING",
  REGISTERED: "REGISTERED",
  UPDATE_READY: "UPDATE_READY",
  ACTIVATED: "ACTIVATED",
  FAILED: "FAILED"
});

export const PWA_SHELL_GENERATION = PWA_CACHE_VERSION;
const FOREGROUND_UPDATE_MIN_INTERVAL_MS = 30_000;

function renderStatus(documentRef, status) {
  if (!documentRef?.querySelectorAll) return;
  for (const element of documentRef.querySelectorAll("[data-role='pwa-status']")) {
    element.textContent = status.replaceAll("_", " ").toLowerCase();
    element.dataset.pwaStatus = status;
  }
}

function exposeGeneration(documentRef) {
  const root = documentRef?.documentElement;
  if (root?.dataset) root.dataset.shellGeneration = PWA_SHELL_GENERATION;
}

export async function registerServiceWorker({
  navigatorRef = globalThis.navigator,
  windowRef = globalThis.window,
  documentRef = globalThis.document,
  scriptUrl = "./sw.js",
  scope = "./",
  now = () => Date.now(),
} = {}) {
  exposeGeneration(documentRef);

  let status = ServiceWorkerStatus.REGISTERING;
  const onShellPartialLoaded = () => renderStatus(documentRef, status);
  documentRef?.addEventListener?.("nexilabs:shell-partial-loaded", onShellPartialLoaded);

  if (!navigatorRef?.serviceWorker?.register) {
    status = ServiceWorkerStatus.UNSUPPORTED;
    renderStatus(documentRef, status);
    return Object.freeze({
      supported: false,
      status,
      registration: null,
      dispose() {
        documentRef?.removeEventListener?.("nexilabs:shell-partial-loaded", onShellPartialLoaded);
      },
    });
  }

  renderStatus(documentRef, status);
  try {
    const registration = await navigatorRef.serviceWorker.register(scriptUrl, { scope, updateViaCache: "none" });
    status = registration.waiting ? ServiceWorkerStatus.UPDATE_READY : ServiceWorkerStatus.REGISTERED;
    let lastUpdateCheckAt = 0;
    let disposed = false;
    let activationRequestedFor = null;
    renderStatus(documentRef, status);

    const activateWaitingWorker = () => {
      const waiting = registration.waiting;
      if (!waiting) return false;
      if (activationRequestedFor === waiting) return true;
      activationRequestedFor = waiting;
      waiting.postMessage({ type: "SKIP_WAITING" });
      return true;
    };

    const announceUpdate = () => {
      status = ServiceWorkerStatus.UPDATE_READY;
      renderStatus(documentRef, status);
      windowRef?.dispatchEvent?.(new CustomEvent("nexilabs:pwa-update-ready", {
        detail: Object.freeze({ generation: PWA_SHELL_GENERATION })
      }));
      // A worker reaches waiting only after its complete APP_SHELL installation promise resolves.
      // Activating here lets a stale controlled page converge without requiring a manual update button.
      activateWaitingWorker();
    };

    if (registration.waiting) announceUpdate();
    registration.addEventListener?.("updatefound", () => {
      const worker = registration.installing;
      worker?.addEventListener?.("statechange", () => {
        if (worker.state === "installed" && navigatorRef.serviceWorker.controller) announceUpdate();
      });
    });

    const onControllerChange = () => {
      status = ServiceWorkerStatus.ACTIVATED;
      renderStatus(documentRef, status);
      windowRef?.dispatchEvent?.(new CustomEvent("nexilabs:pwa-activated", {
        detail: Object.freeze({ generation: PWA_SHELL_GENERATION })
      }));
      // The worker activation lifecycle owns the single stale-client navigation.
      // Do not location.reload() here or one update can cause duplicate browser restarts.
    };
    navigatorRef.serviceWorker.addEventListener?.("controllerchange", onControllerChange);

    const checkForUpdate = async ({ force = false } = {}) => {
      const current = now();
      if (!force && current - lastUpdateCheckAt < FOREGROUND_UPDATE_MIN_INTERVAL_MS) return false;
      lastUpdateCheckAt = current;
      try {
        await registration.update();
        if (registration.waiting) announceUpdate();
        return true;
      } catch {
        // Update discovery is opportunistic. The last valid cached shell remains usable offline.
        return false;
      }
    };

    const onVisibilityChange = () => {
      if (documentRef?.visibilityState === "visible") void checkForUpdate();
    };
    const onPageShow = () => { void checkForUpdate(); };
    documentRef?.addEventListener?.("visibilitychange", onVisibilityChange);
    windowRef?.addEventListener?.("pageshow", onPageShow);

    // Check once after registration without blocking application-shell startup.
    void checkForUpdate({ force: true });

    return Object.freeze({
      supported: true,
      get status() { return status; },
      generation: PWA_SHELL_GENERATION,
      registration,
      activateUpdate: activateWaitingWorker,
      checkForUpdate: () => checkForUpdate({ force: true }),
      dispose() {
        if (disposed) return;
        disposed = true;
        documentRef?.removeEventListener?.("visibilitychange", onVisibilityChange);
        documentRef?.removeEventListener?.("nexilabs:shell-partial-loaded", onShellPartialLoaded);
        windowRef?.removeEventListener?.("pageshow", onPageShow);
        navigatorRef.serviceWorker.removeEventListener?.("controllerchange", onControllerChange);
      }
    });
  } catch (error) {
    status = ServiceWorkerStatus.FAILED;
    renderStatus(documentRef, status);
    return Object.freeze({
      supported: true,
      status,
      registration: null,
      error,
      dispose() {
        documentRef?.removeEventListener?.("nexilabs:shell-partial-loaded", onShellPartialLoaded);
      },
    });
  }
}
