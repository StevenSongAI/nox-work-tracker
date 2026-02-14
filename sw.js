// ============================================
// SERVICE WORKER - Aggressive Cache Busting
// Version: v4-nuclear - Hard reload all data
// ============================================

const CACHE_VERSION = 'v4-nuclear-' + new Date().toISOString().slice(0,10);
const CACHE_NAME = 'worktracker-' + CACHE_VERSION;

// NO static assets cached - everything fetches fresh
const STATIC_ASSETS = [];

// Install: Skip waiting, claim clients immediately
self.addEventListener('install', (event) => {
  console.log('[SW] Installing ' + CACHE_VERSION + '...');
  self.skipWaiting();
});

// Activate: NUKE all old caches
self.addEventListener('activate', (event) => {
  console.log('[SW] ACTIVATING ' + CACHE_VERSION + ' - NUKING ALL CACHES...');
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((name) => {
          console.log('[SW] DELETING:', name);
          return caches.delete(name);
        })
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch: ALWAYS network-first, never cache HTML/JSON
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);
  
  // NEVER cache: JSON, HTML, or root paths
  const isData = url.pathname.endsWith('.json') || 
                 url.pathname.endsWith('.html') ||
                 url.pathname === '/' ||
                 url.pathname === '';
  
  if (isData) {
    event.respondWith(
      fetch(request, { 
        cache: 'no-store',
        headers: { 'Cache-Control': 'no-cache, no-store, must-revalidate' }
      }).catch(() => new Response('{"error":"offline"}', {status: 503}))
    );
    return;
  }
  
  // JS/CSS: Network first, cache fallback (short-lived)
  if (url.pathname.endsWith('.js') || url.pathname.endsWith('.css')) {
    event.respondWith(
      fetch(request, { cache: 'no-store' })
        .then(response => {
          // Update cache in background
          const clone = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(request, clone));
          return response;
        })
        .catch(() => caches.match(request))
    );
    return;
  }
  
  // Default: Network only
  event.respondWith(fetch(request, { cache: 'no-store' }));
});

// Message handler for hard reload
self.addEventListener('message', (event) => {
  if (event.data === 'HARD_RELOAD') {
    console.log('[SW] HARD RELOAD requested');
    caches.keys().then(names => 
      Promise.all(names.map(n => caches.delete(n)))
    ).then(() => {
      event.ports[0].postMessage('RELOADED');
    });
  }
});
