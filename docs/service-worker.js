const CACHE_NAME = 'booze-newz-cache-v2';

const urlsToCache = [
  '/index.html',
  '/style.css',
  '/deals.json',
  '/img/beer-man.png',
  '/android-chrome-192x192.png',
  '/android-chrome-512x512.png'
];

// Install event: pre-cache important files
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(urlsToCache))
  );
});

// Activate event: take control immediately
self.addEventListener('activate', event => {
  event.waitUntil(clients.claim());
});

// Fetch event: try network first, fallback to cache
self.addEventListener('fetch', event => {
  event.respondWith(
    fetch(event.request)
      .then(response => {
        // Clone the response so we can cache it
        const clone = response.clone();
        caches.open(CACHE_NAME).then(cache => {
          cache.put(event.request, clone);
        });
        return response;
      })
      .catch(() => caches.match(event.request)) // fallback if offline
  );
});
