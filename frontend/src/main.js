/** Browser entry point for the NexiLabs PWA. */

import { createRuntimeConfig } from "./config/runtime-config.js";
import { mountNexiLabsShell } from "./app/shell/nexilabs-shell.js";
import { registerServiceWorker } from "./pwa/service-worker-registration.js";

function readPublicRuntimeInput(documentRef) {
  const root = documentRef.documentElement;
  return {
    applicationVersion: root.dataset.applicationVersion || "0.1.0",
    runtimeMode: root.dataset.runtimeMode || "development",
    environmentName: root.dataset.environmentName || "development",
    apiBaseUrl: root.dataset.apiBaseUrl || "",
    buildReference: root.dataset.buildReference || "local-development",
  };
}

export async function bootstrap(documentRef = globalThis.document, windowRef = globalThis.window, fetchRef = globalThis.fetch) {
  const config = createRuntimeConfig(readPublicRuntimeInput(documentRef));

  // Start the offline recovery boundary before shell partial loading. A slow/dead local
  // development server must not prevent the worker from being registered or updated.
  void registerServiceWorker({ documentRef, windowRef });

  const application = await mountNexiLabsShell({ documentRef, windowRef, fetchRef, config });
  void import("./app/account/account-enrollment-experience.js")
    .then(({ installAccountEnrollmentExperience }) => installAccountEnrollmentExperience({ documentRef, windowRef }))
    .catch((error) => console.warn("[NexiLabs PWA] Account enrollment presentation unavailable.", error));

  // P006.UI.10.3: preserve the locked authentication experience while supplying
  // an additive runtime-aware transport. Simulation/Guest development fixtures
  // remain on :8766; Production NexaDevs authentication uses the governed :8767
  // PostgreSQL authority. Admin Layer 2 is attached only after Layer 1 resolves.
  void Promise.all([
    import("./app/auth/authentication-experience.js"),
    import("./app/auth/runtime-auth-client.js"),
  ])
    .then(([{ installAuthenticationExperience }, { createRuntimeAuthClient }]) => {
      const authentication = installAuthenticationExperience({
        documentRef,
        windowRef,
        application,
        client: createRuntimeAuthClient({ fetchRef, windowRef }),
      });
      return import("./app/auth/admin-authentication-experience.js")
        .then(({ installAdminAuthenticationExperience }) => installAdminAuthenticationExperience({
          documentRef,
          windowRef,
          authentication,
        }));
    })
    .catch((error) => console.warn("[NexiLabs PWA] Layered authentication unavailable.", error));

  void import("./app/features/novegeo-national-geography-experience.js")
    .then(({ installNoveGeoNationalGeographyExperience }) => installNoveGeoNationalGeographyExperience({ documentRef, windowRef, fetchRef, apiBaseUrl: config.apiBaseUrl }))
    .catch((error) => console.warn("[NexiLabs PWA] Governed national geography unavailable.", error));
  void import("./app/features/novegeo-cartographic-styling-experience.js")
    .then(({ installNoveGeoCartographicStylingExperience }) => installNoveGeoCartographicStylingExperience({ documentRef, windowRef, fetchRef, apiBaseUrl: config.apiBaseUrl }))
    .catch((error) => console.warn("[NexiLabs PWA] Cartographic styling unavailable.", error));
  void import("./app/features/novegeo-region-map-experience.js")
    .then(({ installNoveGeoRegionMapExperience }) => installNoveGeoRegionMapExperience({ documentRef, windowRef, fetchRef, apiBaseUrl: config.apiBaseUrl }))
    .catch((error) => console.warn("[NexiLabs PWA] Governed REGION cartography unavailable.", error));

  const cityExperience = import("./app/features/novegeo-city-map-experience.js")
    .then(({ installNoveGeoCityMapExperience }) => installNoveGeoCityMapExperience({ documentRef, windowRef, fetchRef, apiBaseUrl: config.apiBaseUrl }))
    .catch((error) => console.warn("[NexiLabs PWA] Governed CITY cartography unavailable.", error));

  // P006.7.11.15.9 compatibility maintenance: future governed map layers register
  // through the generic append-only manifest.  The seam starts only after the locked
  // CITY bootstrap attempt and does not alter REGION/CITY implementation contracts.
  void cityExperience.then(() => import("./app/features/novegeo-map-extension-loader.js"))
    .then(({ installNoveGeoMapExtensions }) => installNoveGeoMapExtensions({
      documentRef,
      windowRef,
      fetchRef,
      apiBaseUrl: config.apiBaseUrl,
    }))
    .catch((error) => console.warn("[NexiLabs PWA] Governed map extensions unavailable.", error));

  return application;
}

if (typeof document !== "undefined") {
  void bootstrap(document, globalThis.window, globalThis.fetch).catch((error) => {
    console.error("[NexiLabs PWA] Application bootstrap failed.", error);
  });
}
