const CACHE_NAME = "vigilachile-v10";
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
          return caches.delete(key);
        })
      );
    }).then(function() {
      return self.clients.claim();
    })
  );
});

// Fetch — Network First para todo (evita cachés desactualizados)
self.addEventListener("fetch", function(e) {
  var url = new URL(e.request.url);

  // Backend API — siempre network
  if (url.hostname.includes("onrender.com") || url.port === "8000") {
    e.respondWith(fetch(e.request).catch(function() {
      return new Response(
        JSON.stringify({ error: "Sin conexión al servidor" }),
        { headers: { "Content-Type": "application/json" } }
      );
    }));
    return;
  }

  // Todo lo demás — network first, cache fallback
  e.respondWith(
    fetch(e.request).then(function(response) {
      if (response && response.status === 200) {
        var clone = response.clone();
        caches.open(CACHE_NAME).then(function(cache) {
          cache.put(e.request, clone);
        });
      }
      return response;
    }).catch(function() {
      return caches.match(e.request);
    })
  );
});

self.addEventListener("message", function(e) {
  if (e.data === "skipWaiting") {
    self.skipWaiting();
  }
});