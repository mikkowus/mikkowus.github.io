// Service worker for add-location.html: caches just enough of the app shell
// that the form loads with no connectivity. Everything else (API calls to
// the Worker, OSM map tiles) goes straight to the network -- offline support
// here means "the form works", not "the map preview works with no signal".

const CACHE_NAME = 'add-location-shell-v1';

const SHELL_URLS = [
  'add-location.html',
  'shared.js',
  'offline-queue.js',
  'manifest.json',
  'icons/launch-192.png',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(SHELL_URLS))
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key)))
    )
  );
});

self.addEventListener('fetch', (event) => {
  const isShellAsset = SHELL_URLS.some((url) => event.request.url.endsWith(url));
  if (!isShellAsset) return; // let the browser handle API/tile requests normally

  event.respondWith(
    caches.match(event.request).then((cached) => cached || fetch(event.request))
  );
});
