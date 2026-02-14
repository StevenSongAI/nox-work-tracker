// ============================================
// SERVICE WORKER - Cache Control for Work Tracker
// Prevents stale JSON data by bypassing cache for API calls
// ============================================

const CACHE_NAME = 'worktracker-v2026-02-14-v3-forced';

// Files to cache (static assets only - NOT JSON data, NOT HTML)
const STATIC_ASSETS = [
  '/nox-work-tracker/app.js',
  'https://cdn.tailwindcss.com',
  'https://cdn.jsdelivr.net/npm/chart.js'
];

// Install: Skip waiting immediately to activate new SW
self.addEventListener('install', (event) => {
  console.log('[SW] Installing v3-forced...');
  self.skipWaiting();
});

// Activate: Clean up ALL old caches immediately
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating v3-forced - clearing all old caches...');
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((name) => {
          console.log('[SW] Deleting old cache:', name);
          return caches.delete(name);
        })
      );
    }).then(() => {
      console.log('[SW] Claiming all clients...');
      return self.clients.claim();
    })
  );
});

// Fetch: Network-first for JSON and HTML, cache-first for static assets
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);
  
  // NEVER cache JSON data files OR HTML pages - always fetch fresh
  if (url.pathname.endsWith('.json') || url.pathname.endsWith('.html') || url.pathname === '/nox-work-tracker/' || url.pathname === '/nox-work-tracker') {
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
