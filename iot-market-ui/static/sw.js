// Minimal service worker so iOS treats the app as installable.
// We don't precache — the marketplace pages need fresh contract reads,
// so a network-first strategy with a no-op SW is enough to satisfy
// the PWA install heuristics.
self.addEventListener('install', () => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener('fetch', () => {
  // pass-through — let the browser handle it
});
