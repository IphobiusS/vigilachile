const CACHE_NAME = "vigilachile-v6";
const STATIC_ASSETS = [
  "/",
  "/index.html",
  "/styles.css",
  "/app.js",
  "/manifest.json"
];

// Instalar — cachear assets estáticos
self.addEventListener("install", function(e) {
  e.waitUntil(
    caches.open(CACHE_NAME).then(function(cache) {
      return cache.addAll(STATIC_ASSETS);
    }).then(function() {
      return self.skipWaiting();
    })
  );
});

// Activar — eliminar cachés viejos
self.addEventListener("activate", function(e) {
  e.waitUntil(
    caches.keys().then(function(keys) {
      return Promise.all(
        keys.filter(function(key) {
          return key !== CACHE_NAME;
        }).map(function(key) {
          console.log("GeoAlert SW: eliminando caché viejo:", key);
          return caches.delete(key);
        })
      );
    }).then(function() {
      return self.clients.claim();
    })
  );
});

// Fetch — estrategia Network First para APIs, Cache First para assets
self.addEventListener("fetch", function(e) {
  const url = new URL(e.request.url);

  // Requests al backend — siempre network, nunca cachear
  if (url.port === "8000" || url.hostname === "127.0.0.1" || url.hostname.includes("onrender.com")) {
    e.respondWith(fetch(e.request).catch(function() {
      return new Response(
        JSON.stringify({ error: "Sin conexión al servidor" }),
        { headers: { "Content-Type": "application/json" } }
      );
    }));
    return;
  }

  // Assets externos (Leaflet, Chart.js, CDNs) — network first
  if (url.hostname !== self.location.hostname) {
    e.respondWith(
      fetch(e.request).catch(function() {
        return caches.match(e.request);
      })
    );
    return;
  }

  // Assets locales (html, css, js) — NETWORK FIRST, fallback a cache
  e.respondWith(
    fetch(e.request).then(function(response) {
      // Actualizar cache con versión nueva
      if (response && response.status === 200) {
        var clone = response.clone();
        caches.open(CACHE_NAME).then(function(cache) {
          cache.put(e.request, clone);
        });
      }
      return response;
    }).catch(function() {
      // Sin red — servir desde cache
      return caches.match(e.request);
    })
  );
});

// Mensaje para forzar actualización desde app.js si es necesario
self.addEventListener("message", function(e) {
  if (e.data === "skipWaiting") {
    self.skipWaiting();
  }
});