// ============================================
// SERVICE WORKER - Cache Control for Work Tracker
// Prevents stale JSON data by bypassing cache for API calls
// ============================================

const CACHE_NAME = 'worktracker-v2025-03-06-v2';

// Files to cache (static assets only - NOT JSON data)
const STATIC_ASSETS = [
  '/nox-work-tracker/',
  '/nox-work-tracker/index.html',
  '/nox-work-tracker/app.js',
  'https://cdn.tailwindcss.com',
  'https://cdn.jsdelivr.net/npm/chart.js'
];

// Install: Pre-cache static assets
self.addEventListener('install', (event) => {
  console.log('[SW] Installing...');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(STATIC_ASSETS))
      .then(() => self.skipWaiting())
  );
});

// Activate: Clean up old caches
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating...');
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name !== CACHE_NAME)
          .map((name) => caches.delete(name))
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch: Network-first for JSON, cache-first for static assets
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);
  
  // NEVER cache JSON data files - always fetch fresh
  if (url.pathname.endsWith('.json')) {
    event.respondWith(
      fetch(request, { cache: 'no-store' })
        .catch(() => caches.match(request))
    );
    return;
  }
  
  // Cache-busting query param detected - force network fetch
  if (url.search.includes('_=')) {
    event.respondWith(
      fetch(request, { cache: 'no-store' })
        .catch(() => caches.match(request))
    );
    return;
  }
  
  // Static assets: Cache first, network fallback
  if (STATIC_ASSETS.includes(url.pathname)) {
    event.respondWith(
      caches.match(request)
        .then((response) => response || fetch(request))
    );
    return;
  }
  
  // Default: Network with cache fallback
  event.respondWith(
    fetch(request)
      .catch(() => caches.match(request))
  );
});

// Message handler for cache clearing
self.addEventListener('message', (event) => {
  if (event.data === 'CLEAR_CACHES') {
    caches.keys().then((cacheNames) => {
      return Promise.all(cacheNames.map((name) => caches.delete(name)));
    }).then(() => {
      event.ports[0].postMessage('CACHES_CLEARED');
    });
  }
});
