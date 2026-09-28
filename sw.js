/**
 * Service worker de BeerWalk Madrid.
 *
 * Estrategia: cache-first para el app shell y los assets propios (todo lo que
 * vive en este repo), network-first para los CDNs de Leaflet y las fuentes, de
 * modo que una version nueva del mapa llegue sin esperar al SW.
 *
 * Solo se registra fuera de la app nativa: bajo capacitor:// no aplica.
 */
const VERSION = "beerwalk-v3";
const SHELL_CACHE = VERSION + "-shell";
const RUNTIME_CACHE = VERSION + "-runtime";

// Rutas relativas a la raiz del sitio (GitHub Pages sirve en /beerwalk-madrid/).
const PRECACHE = [
  "./",
  "./index.html",
  "./native.js",
  "./manifest.webmanifest",
  "./icons/icon-192.png",
  "./icons/icon-512.png",
  "./icons/maskable-192.png",
  "./icons/maskable-512.png",
  "./icons/apple-touch-icon.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(SHELL_CACHE)
      // addAll() es atomico: si un solo recurso falla no se instala nada.
      .then((cache) => Promise.allSettled(PRECACHE.map((url) => cache.add(url))))
      .then(() => self.skipWaiting())
  );
});

// Sin esto, un SW nuevo convive con el viejo y los usuarios se quedan
// clavados en la version cacheada hasta recargar dos veces.
self.addEventListener("message", (event) => {
  if (event.data === "skip-waiting") self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys.filter((key) => !key.startsWith(VERSION)).map((key) => caches.delete(key))
        )
      )
      .then(() => self.clients.claim())
      // claim()接管 paginas ya abiertas, pero su HTML sigue siendo el viejo
      // hasta que recargan. Avisarles evita la sensacion de app rota.
      .then(() =>
        self.clients.matchAll({ type: "window" }).then((clients) =>
          clients.forEach((c) => c.postMessage({ type: "new-version" }))
        )
      )
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;

  if (req.method !== "GET") return;

  const url = new URL(req.url);

  // Las peticiones a la API de Google necesitan red y nunca se cachean.
  if (url.hostname.endsWith("googleapis.com") || url.hostname.endsWith("google.com")) return;

  // App shell y recursos propios.
  //
  // El HTML va red-primero a proposito: index.html *es* la aplicacion, y con
  // cache-first un despliegue nuevo no llega a quien ya visito la web (el SW
  // le devolveria la version anterior indefinidamente). Sin red se cae a la
  // cache, que es justo el caso offline.
  //
  // El resto (native.js, manifest, iconos) si va cache-first: cambian poco y
  // interesa que carguen de inmediato.
  if (url.origin === self.location.origin) {
    const isHTML =
      req.mode === "navigate" || (req.headers.get("accept") || "").includes("text/html");

    if (isHTML) {
      event.respondWith(
        fetch(req)
          .then((res) => {
            if (res && res.ok) {
              const copy = res.clone();
              caches.open(SHELL_CACHE).then((c) => c.put(req, copy));
              return res;
            }
            // 4xx/5xx: servidor caido, portal cautivo, proxy... mejor la cache
            // que dejar al usuario mirando una pagina de error.
            return caches.match(req).then((r) => r || caches.match("./index.html"));
          })
          .catch(() => caches.match(req).then((r) => r || caches.match("./index.html")))
      );
      return;
    }

    event.respondWith(
      caches.match(req).then((cached) => {
        const network = fetch(req)
          .then((res) => {
            if (res && res.status === 200 && res.type === "basic") {
              const copy = res.clone();
              caches.open(SHELL_CACHE).then((c) => c.put(req, copy));
            }
            return res;
          })
          .catch(() => cached);

        return cached || network;
      })
    );
    return;
  }

  // CDNs externos: red primero, cache como respaldo.
  event.respondWith(
    fetch(req)
      .then((res) => {
        if (res && res.status === 200 && res.type === "cors") {
          const copy = res.clone();
          caches.open(RUNTIME_CACHE).then((c) => c.put(req, copy));
        }
        return res;
      })
      .catch(() => caches.match(req))
  );
});
