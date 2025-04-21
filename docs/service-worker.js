const CACHE_NAME = 'booze-newz-cache-v1';
const urlsToCache = [
  '/index.html',
  '/style.css',
  '/deals.json',
  '/img/beer-man.png',
  '/android-chrome-192x192.png',
  '/android-chrome-512x512.png'
];

// Install
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(urlsToCache))
  );
});

// Fetch
self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => response || fetch(event.request))
  );
});
