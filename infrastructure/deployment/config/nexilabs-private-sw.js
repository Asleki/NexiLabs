/**
 * NEXILABS.PAB.1 private-development service-worker boundary.
 *
 * DEVELOPMENT_PRIVATE deliberately disables the normal offline PWA shell.
 * This worker clears NexiLabs caches and unregisters itself. The next
 * navigation must therefore reach the HTTPS edge and pass Google allowlist
 * authorization.
 */
self.addEventListener("install", (event) => {
  event.waitUntil(self.skipWaiting());
});

self.addEventListener("activate", (event) => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(
      keys
        .filter((key) => key.startsWith("nexilabs-"))
        .map((key) => caches.delete(key))
    );
    await self.registration.unregister();
    const clients = await self.clients.matchAll({
      type: "window",
      includeUncontrolled: true,
    });
    await Promise.all(
      clients.map((client) => {
        if (!client.url?.startsWith(self.location.origin)) return undefined;
        return client.navigate(client.url);
      })
    );
  })());
});
