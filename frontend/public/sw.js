/* Only generic public files belong here. Never cache HTML app routes, RSC,
 * API responses, student profiles, recommendations, or chat. Bump this version
 * when changing a precached asset. */
const CACHE_NAME = "lifepilot-public-v1";
const PUBLIC_FILES = [
  "/offline.html",
  "/offline.css",
  "/manifest.webmanifest",
  "/icons/icon-192.png",
  "/icons/icon-512.png",
  "/icons/icon-maskable-512.png",
  "/icons/apple-touch-icon.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE_NAME);
    // Reload the public shell even if the HTTP cache has an older version.
    await cache.addAll(PUBLIC_FILES.map((url) => new Request(url, { cache: "reload" })));
  })());
  // Updates wait until the old app is closed; never reload a student's active form.
});

self.addEventListener("activate", (event) => {
  event.waitUntil((async () => {
    for (const name of await caches.keys()) {
      if (name.startsWith("lifepilot-public-") && name !== CACHE_NAME) {
        await caches.delete(name);
      }
    }
    await self.clients.claim();
  })());
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== "GET" || url.origin !== self.location.origin) return;
  if (url.pathname === "/api" || url.pathname.startsWith("/api/")) return;

  if (request.mode === "navigate") {
    event.respondWith((async () => {
      try {
        // Even visited app pages stay network-only, outside the HTTP cache.
        return await fetch(new Request(request, { cache: "no-store" }));
      } catch {
        const offline = await caches.match("/offline.html", { cacheName: CACHE_NAME });
        return offline || new Response("You are offline. Reconnect and try again.", {
          status: 503, headers: { "Content-Type": "text/plain; charset=utf-8" },
        });
      }
    })());
    return;
  }

  if (!url.search && PUBLIC_FILES.includes(url.pathname)) {
    event.respondWith((async () => {
      const cached = await caches.match(request, { cacheName: CACHE_NAME });
      return cached || fetch(request);
    })());
  }
});
