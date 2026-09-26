/** P006.UI.1 / Bundle 12.0C — Shared HTML partial loader with bounded startup waits. */
export const ShellPartial = Object.freeze({
  HEADER: Object.freeze({ slot: "[data-shell-slot='header']", url: "./src/ui/partials/header.html" }),
  FOOTER: Object.freeze({ slot: "[data-shell-slot='footer']", url: "./src/ui/partials/footer.html" }),
});

export const DEFAULT_PARTIAL_TIMEOUT_MS = 1800;

function timeoutError(url, timeoutMs) {
  const error = new Error(`Timed out loading shell partial after ${timeoutMs}ms: ${url}`);
  error.name = "ShellPartialTimeoutError";
  return error;
}

async function fetchWithTimeout(fetchRef, url, timeoutMs) {
  if (!Number.isFinite(timeoutMs) || timeoutMs <= 0) return fetchRef(url, { cache: "no-cache" });

  const controller = typeof AbortController === "function" ? new AbortController() : null;
  let timer;
  const timeout = new Promise((_, reject) => {
    timer = setTimeout(() => {
      controller?.abort?.();
      reject(timeoutError(url, timeoutMs));
    }, timeoutMs);
  });

  try {
    return await Promise.race([
      fetchRef(url, { cache: "no-cache", ...(controller ? { signal: controller.signal } : {}) }),
      timeout,
    ]);
  } finally {
    clearTimeout(timer);
  }
}

export function shellPartialsReady(documentRef) {
  return Object.values(ShellPartial).every((descriptor) => {
    const slot = documentRef?.querySelector?.(descriptor.slot);
    return slot?.dataset?.partialReady === "true";
  });
}

export async function loadPartial({
  documentRef,
  fetchRef = globalThis.fetch,
  descriptor,
  timeoutMs = DEFAULT_PARTIAL_TIMEOUT_MS,
}) {
  if (!documentRef?.querySelector) throw new TypeError("documentRef must provide querySelector");
  if (typeof fetchRef !== "function") throw new TypeError("fetchRef must be a function");
  if (!descriptor?.slot || !descriptor?.url) throw new TypeError("descriptor must define slot and url");

  const slot = documentRef.querySelector(descriptor.slot);
  if (!slot) throw new Error(`Shell partial slot not found: ${descriptor.slot}`);

  const response = await fetchWithTimeout(fetchRef, descriptor.url, timeoutMs);
  if (!response?.ok) throw new Error(`Failed to load shell partial: ${descriptor.url}`);

  slot.innerHTML = await response.text();
  slot.dataset.partialReady = "true";
  delete slot.dataset.partialError;

  // Shell chrome can mount after independent runtime state has already settled.
  // Announce every successful partial insertion so state owners can replay
  // their current presentation into newly-created header/footer elements.
  if (typeof Event === "function") {
    documentRef.dispatchEvent?.(new Event("nexilabs:shell-partial-loaded"));
  }

  return Object.freeze({ slot: descriptor.slot, url: descriptor.url, ready: true });
}

export async function loadShellPartials(options = {}) {
  return Promise.all([
    loadPartial({ ...options, descriptor: ShellPartial.HEADER }),
    loadPartial({ ...options, descriptor: ShellPartial.FOOTER }),
  ]);
}
