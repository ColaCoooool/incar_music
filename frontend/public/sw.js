/* InCar Music service worker: shell + offline audio (cache-first for /api/stream/*) */
const SHELL_CACHE = 'incar-shell-v1'
const AUDIO_CACHE = 'incar-audio-v1'

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(SHELL_CACHE).then((c) => c.addAll(['/'])))
  self.skipWaiting()
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((k) => k !== SHELL_CACHE && k !== AUDIO_CACHE)
          .map((k) => caches.delete(k))
      )
    )
  )
  self.clients.claim()
})

self.addEventListener('fetch', (event) => {
  const req = event.request
  if (req.method !== 'GET') return
  const url = new URL(req.url)

  // Audio streams: cache-first, backfill on success (playback = offline enablement)
  if (url.pathname.startsWith('/api/stream/')) {
    event.respondWith(
      caches.open(AUDIO_CACHE).then(async (cache) => {
        const hit = await cache.match(req)
        if (hit) return hit
        const resp = await fetch(req)
        if (resp.ok) cache.put(req, resp.clone())
        return resp
      })
    )
    return
  }

  // Static assets: cache-first with runtime backfill
  const isStatic =
    url.origin === self.location.origin &&
    (url.pathname.startsWith('/assets/') ||
      url.pathname.startsWith('/icons/') ||
      url.pathname === '/manifest.webmanifest')
  if (isStatic) {
    event.respondWith(
      caches.open(SHELL_CACHE).then(async (cache) => {
        const hit = await cache.match(req)
        if (hit) return hit
        const resp = await fetch(req)
        if (resp.ok) cache.put(req, resp.clone())
        return resp
      })
    )
  }
  // Other /api/* requests: network only (not intercepted)
})
