/** P003.2–P003.4 / P006.UI.10.1.R2 / PTB.11 — v17 shell with live-authority cache boundary. */
const CACHE_NAME = "nexilabs-shell-v17";
const SAME_GENERATION_REFRESH_MARKER = "nexilabs-refresh-p006-7-11-15-4-r2";
const REGION_SAME_GENERATION_REFRESH_MARKER = "nexilabs-refresh-p006-7-11-15-6-r1";
const CITY_SAME_GENERATION_REFRESH_MARKER = "nexilabs-refresh-p006-7-11-15-7-r1";
const MAP_EXTENSION_SEAM_SAME_GENERATION_REFRESH_MARKER = "nexilabs-refresh-p006-7-11-15-9-compat-seam-r1";
const MAP_FIRST_PRESENTATION_SAME_GENERATION_REFRESH_MARKER = "nexilabs-refresh-p006-7-11-15-10-r2";
const STYLING_ARCHITECTURE_LOCK_SAME_GENERATION_REFRESH_MARKER = "nexilabs-refresh-p006-7-11-15-10-1";
const UNIFIED_ENVIRONMENTAL_COMPOSITION_SAME_GENERATION_REFRESH_MARKER = "nexilabs-refresh-p006-7-11-15-10-1-3";
const ACCOUNT_ENROLLMENT_ACTIVATION_SAME_GENERATION_REFRESH_MARKER = "nexilabs-refresh-p006-ui-10-1-r2";
const FRONTEND_ACCESS_INTEGRATION_SAME_GENERATION_REFRESH_MARKER = "nexilabs-refresh-p006-ui-10-4-r2";
const OFFLINE_URL = "./index.html";
const NAVIGATION_NETWORK_TIMEOUT_MS = 1800;
const LIVE_AUTHORITY_PATH_PREFIXES = Object.freeze([
  "/oauth2",
  "/auth",
  "/api/v1",
]);

const FRONTEND_ACCESS_INTEGRATION_PATHS = Object.freeze([
  "/src/app/account/account-enrollment-experience.js",
  "/src/app/admin/admin-review-view-model.js",
  "/src/app/auth/admin-authentication-experience.js",
  "/src/app/auth/production-auth-client-p006-ui-10-4.js",
  "/src/app/auth/runtime-auth-client.js",
  "/src/ui/pages/admin-workspace.js",
  "/src/ui/pages/developer-account-enrollment-p006-ui-10-4.js",
]);

function isFrontendAccessIntegrationPath(pathname) {
  return FRONTEND_ACCESS_INTEGRATION_PATHS.includes(pathname);
}

function isLiveAuthorityPath(pathname) {
  return LIVE_AUTHORITY_PATH_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`)
  );
}

function isLiveAuthorityRequest(request) {
  const url = new URL(request.url);
  return url.origin === self.location.origin && isLiveAuthorityPath(url.pathname);
}

async function removeCachedLiveAuthorityResponses(cache) {
  const requests = await cache.keys();
  await Promise.all(
    requests
      .filter((request) => isLiveAuthorityRequest(request))
      .map((request) => cache.delete(request))
  );
}

async function frontendAccessIntegrationResponse(request) {
  try {
    const response = await fetch(request, { cache: "no-store" });

    if (response && response.status === 200 && response.type !== "opaque") {
      const cache = await caches.open(CACHE_NAME);
      await cache.put(request, response.clone());
    }

    return response;
  } catch (error) {
    const cached = await caches.match(request);
    if (cached) return cached;
    throw error;
  }
}

const APP_SHELL = [
  "./",
  "./index.html",
  "./public/manifest.webmanifest",
  "./public/brand/nexilabs/metadata/brand-tokens.css",
  "./public/brand/nexilabs/vectors/nexilabs_logo_horizontal.svg",
  "./public/brand/nexilabs/pwa/nexilabs_icon_192x192.png",
  "./public/brand/nexilabs/pwa/nexilabs_icon_512x512.png",
  "./public/brand/nexilabs/pwa/nexilabs_maskable_192x192.png",
  "./public/brand/nexilabs/pwa/nexilabs_maskable_512x512.png",
  "./styles/app.css",
  "./styles/account-enrollment-v1.css",
  "./styles/novegeo-map-shell-v1.css",
  "./styles/novegeo-cartography-v1.css",
  "./styles/novegeo-map-first-v1.css",
  "./src/main.js",
  "./src/app/account/account-enrollment-route.js",
  "./src/app/account/account-enrollment-experience.js",
  "./src/app/admin/admin-review-view-model.js",
  "./src/app/auth/admin-authentication-experience.js",
  "./src/app/auth/production-auth-client-p006-ui-10-4.js",
  "./src/app/auth/runtime-auth-client.js",
  "./src/ui/pages/admin-workspace.js",
  "./src/ui/pages/developer-account-enrollment-p006-ui-10-4.js",
  "./src/ui/partials/header.html",
  "./src/ui/partials/footer.html",
  "./src/app/navigation/application-route.js",
  "./src/app/navigation/application-router.js",
  "./src/app/navigation/runtime-selection.js",
  "./src/app/shell/partial-loader.js",
  "./src/app/shell/shell-recovery.js",
  "./src/app/shell/nexilabs-shell.js",
  "./src/ui/navigation/primary-navigation.js",
  "./src/ui/pages/runtime-gateway.js",
  "./src/ui/pages/account-enrollment-gateway.js",
  "./src/ui/pages/guest-account-enrollment.js",
  "./src/ui/pages/developer-account-enrollment.js",
  "./src/ui/pages/production-access.js",
  "./src/ui/pages/simulation-entry.js",
  "./src/ui/pages/access-placeholder.js",
  "./src/ui/pages/simulation-workspace.js",
  "./src/ui/pages/novegeo-feature.js",
  "./src/ui/pages/production-feature-guard.js",
  "./src/app/workspaces/workspace-capabilities.js",
  "./src/app/features/novegeo-feature-runtime.js",
  "./src/app/features/novegeo-live-authority-runtime.js",
  "./src/app/features/novegeo-map-shell-hardening-runtime.js",
  "./src/app/features/novegeo-feature-geometry.js",
  "./src/app/features/novegeo-national-geography-experience.js",
  "./src/app/features/novegeo-cartographic-styling-experience.js",
  "./src/app/features/novegeo-region-map-experience.js",
  "./src/app/features/novegeo-city-map-experience.js",
  "./src/app/features/novegeo-municipality-map-experience.js",
  "./src/app/features/novegeo-city-district-map-experience.js",
  "./src/app/features/novegeo-town-map-experience.js",
  "./src/app/features/novegeo-map-extension-loader.js",
  "./src/app/features/novegeo-presentation-provider.js",
  "./src/app/application.js",
  "./src/branding/brand-assets.js",
  "./src/branding/brand-config.js",
  "./src/config/runtime-config.js",
  "./src/config/live-api-endpoint.js",
  "./src/core/application-state.js",
  "./src/pwa/cache-policy.js",
  "./src/pwa/service-worker-registration.js",
  "./src/map/nngla/contracts.js",
  "./src/map/nngla/live-contracts.js",
  "./src/map/nngla/live-read-client.js",
  "./src/map/nngla/live-publication-status.js",
  "./src/map/nngla/read-client.js",
  "./src/map/nngla/render-plan.js",
  "./src/map/nngla/publication-status.js",
  "./src/map/nngla/national-map-client.js",
  "./src/map/nngla/governed-snapshot-loader.js",
  "./src/map/nngla/national-map-contracts.js",
  "./src/map/nngla/national-map-state.js",
  "./src/map/geography/contracts.js",
  "./src/map/geography/live-boundary-client.js",
  "./src/map/geography/projection.js",
  "./src/map/geography/status.js",
  "./src/map/presentation/boundary-render-plan.js",
  "./src/map/presentation/canvas-renderer.js",
  "./src/map/presentation/contracts.js",
  "./src/map/presentation/coordinate-grid.js",
  "./src/map/presentation/coordinate-labels.js",
  "./src/map/presentation/index.js",
  "./src/map/presentation/map-presentation.js",
  "./src/map/presentation/publication.js",
  "./src/map/presentation/viewport.js",
  "./src/map/cartography/contracts.js",
  "./src/map/cartography/style-catalog.js",
  "./src/map/cartography/country-anchor.js",
  "./src/map/cartography/label-plan.js",
  "./src/map/cartography/collision.js",
  "./src/map/cartography/label-renderer.js",
  "./src/map/cartography/cartographic-overlay.js",
  "./src/map/cartography/region-anchor.js",
  "./src/map/cartography/region-cartographic-overlay.js",
  "./src/map/cartography/city-anchor.js",
  "./src/map/cartography/city-cartographic-overlay.js",
  "./src/map/cartography/municipality-anchor.js",
  "./src/map/cartography/municipality-cartographic-overlay.js",
  "./src/map/cartography/city-district-anchor.js",
  "./src/map/cartography/city-district-cartographic-overlay.js",
  "./src/map/cartography/town-anchor.js",
  "./src/map/cartography/town-cartographic-overlay.js",
  "./src/map/cartography/semantic-zoom-v2.js",
  "./src/map/cartography/geodesic-scale-v2.js",
  "./src/map/cartography/unified-projection.js",
  "./src/map/cartography/unified-frame-plan.js",
  "./src/map/cartography/unified-environmental-compositor.js",
  "./src/map/cartography/unified-frame-renderer.js",
  "./src/map/cartography/presentation-coordinator.js",
  "./src/map/publication/contracts.js",
  "./src/map/publication/catalog.js",
  "./src/map/publication/index.js",
  "./src/map/publication/v002-overview.js",
  "./src/map/publication/v002-standard.js",
  "./public/geography/novegeo/world-boundary/v002/manifest.json",
  "./public/geography/novegeo/world-boundary/v002/overview.geojson",
  "./public/geography/novegeo/world-boundary/v002/standard.geojson",
  "./public/geography/novegeo/map-extensions/manifest.json",
  "./src/map/validation/contracts.js",
  "./src/map/validation/geometry-validator.js",
  "./src/map/validation/extent-calculator.js",
  "./src/map/validation/extent-validator.js",
  "./src/map/validation/projection-validator.js",
  "./src/map/validation/viewport-validator.js",
  "./src/map/validation/map-shell-safe-area.js",
  "./src/map/validation/qualification.js",
  "./src/map/validation/index.js",
  "./src/map/terrain/contracts.js",
  "./src/map/terrain/catalog.js",
  "./src/map/terrain/render-plan.js",
  "./src/map/landforms/contracts.js",
  "./src/map/landforms/catalog.js",
  "./src/map/landforms/render-plan.js",
  "./src/map/environment/physical-land-presentation.js",
  "./src/map/environment/full-viewport-coordinate-presentation.js",
  "./src/map/lifecycle/foreground-recovery.js",
  "./src/map/hydrology/contracts.js",
  "./src/map/hydrology/catalog.js",
  "./src/map/hydrology/render-plan.js",
  "./src/map/climate/contracts.js",
  "./src/map/climate/catalog.js",
  "./src/map/climate/render-plan.js",
  "./src/map/environment/hydrology-atmosphere-presentation.js",
  "./src/map/vegetation/contracts.js",
  "./src/map/vegetation/catalog.js",
  "./src/map/vegetation/render-plan.js",
  "./src/map/environment/biosphere-presentation.js",
  "./src/map/interaction/navigation-state.js",
  "./src/map/interaction/navigation-controller.js",
  "./src/map/interaction/input-bindings.js",
  "./src/map/interaction/map-navigation-discovery.js",
  "./src/map/controls/layer-state.js",
  "./src/map/controls/novegeo-map-shell.js",
  "./src/map/controls/national-layer-status.js",
  "./src/map/controls/scale.js",
  "./src/map/selection/coordinate-search.js",
  "./src/map/selection/location-selection.js",
  "./src/map/state/view-state-contracts.js",
  "./src/map/state/view-state-storage.js",
  "./src/map/state/view-state-runtime.js",
  "./src/map/state/world-state-contracts.js",
  "./src/map/state/world-state-store.js",
  "./src/map/state/world-state-runtime.js",
  "./src/map/state/p006-state-integration.js",
  "./public/geography/novegeo/vegetation/v001/manifest.json",
  "./public/geography/novegeo/vegetation/v001/standard.json",
  "./public/geography/novegeo/hydrology/v001/manifest.json",
  "./public/geography/novegeo/hydrology/v001/standard.json",
  "./public/geography/novegeo/climate/v001/manifest.json",
  "./public/geography/novegeo/climate/v001/standard.json",
  "./public/geography/novegeo/terrain/v001/manifest.json",
  "./public/geography/novegeo/terrain/v001/overview.json",
  "./public/geography/novegeo/terrain/v001/standard.json",
  "./public/geography/novegeo/landforms/v001/manifest.json",
  "./public/geography/novegeo/landforms/v001/standard.geojson",
];

self.addEventListener("install", (event) => {
  event.waitUntil((async () => {
    const existingKeys = await caches.keys();
    const refreshingExistingGeneration = existingKeys.includes(CACHE_NAME);

    const cache = await caches.open(CACHE_NAME);
    await cache.addAll(APP_SHELL);

    if (refreshingExistingGeneration) {
      await caches.open(SAME_GENERATION_REFRESH_MARKER);
      await caches.open(REGION_SAME_GENERATION_REFRESH_MARKER);
      await caches.open(CITY_SAME_GENERATION_REFRESH_MARKER);
      await caches.open(MAP_EXTENSION_SEAM_SAME_GENERATION_REFRESH_MARKER);
      await caches.open(MAP_FIRST_PRESENTATION_SAME_GENERATION_REFRESH_MARKER);
      await caches.open(STYLING_ARCHITECTURE_LOCK_SAME_GENERATION_REFRESH_MARKER);
      await caches.open(UNIFIED_ENVIRONMENTAL_COMPOSITION_SAME_GENERATION_REFRESH_MARKER);
      await caches.open(ACCOUNT_ENROLLMENT_ACTIVATION_SAME_GENERATION_REFRESH_MARKER);
      await caches.open(FRONTEND_ACCESS_INTEGRATION_SAME_GENERATION_REFRESH_MARKER);
    }

    await self.skipWaiting();
  })());
});

self.addEventListener("activate", (event) => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    const sameGenerationRefresh = keys.includes(SAME_GENERATION_REFRESH_MARKER)
      || keys.includes(REGION_SAME_GENERATION_REFRESH_MARKER)
      || keys.includes(CITY_SAME_GENERATION_REFRESH_MARKER)
      || keys.includes(MAP_EXTENSION_SEAM_SAME_GENERATION_REFRESH_MARKER)
      || keys.includes(MAP_FIRST_PRESENTATION_SAME_GENERATION_REFRESH_MARKER)
      || keys.includes(STYLING_ARCHITECTURE_LOCK_SAME_GENERATION_REFRESH_MARKER)
      || keys.includes(UNIFIED_ENVIRONMENTAL_COMPOSITION_SAME_GENERATION_REFRESH_MARKER)
      || keys.includes(ACCOUNT_ENROLLMENT_ACTIVATION_SAME_GENERATION_REFRESH_MARKER)
      || keys.includes(FRONTEND_ACCESS_INTEGRATION_SAME_GENERATION_REFRESH_MARKER);
    const previousShellKeys = keys.filter(
      (key) => key.startsWith("nexilabs-shell-") && key !== CACHE_NAME
    );

    const cache = await caches.open(CACHE_NAME);
    await removeCachedLiveAuthorityResponses(cache);
    await Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key)));
    await self.clients.claim();

    if (previousShellKeys.length > 0 || sameGenerationRefresh) {
      const clients = await self.clients.matchAll({ type: "window", includeUncontrolled: true });
      await Promise.all(clients.map((client) => {
        if (!client.url?.startsWith(self.location.origin)) return undefined;
        return client.navigate(client.url);
      }));
    }
  })());
});

self.addEventListener("message", (event) => {
  if (event.data?.type === "SKIP_WAITING") self.skipWaiting();
});

async function navigationResponse(request) {
  const controller = typeof AbortController === "function" ? new AbortController() : null;
  let timer;
  try {
    if (controller) timer = setTimeout(() => controller.abort(), NAVIGATION_NETWORK_TIMEOUT_MS);
    return await fetch(request, controller ? { signal: controller.signal } : undefined);
  } catch {
    return (await caches.match(request)) || caches.match(OFFLINE_URL);
  } finally {
    if (timer) clearTimeout(timer);
  }
}

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  if (isLiveAuthorityPath(url.pathname)) {
    event.respondWith(fetch(request, { cache: "no-store" }));
    return;
  }

  if (isFrontendAccessIntegrationPath(url.pathname)) {
    event.respondWith(frontendAccessIntegrationResponse(request));
    return;
  }

  if (request.mode === "navigate") {
    event.respondWith(navigationResponse(request));
    return;
  }

  event.respondWith(
    caches.match(request).then((cached) => cached || fetch(request).then((response) => {
      if (!response || response.status !== 200 || response.type === "opaque") return response;
      const copy = response.clone();
      caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
      return response;
    }))
  );
});
