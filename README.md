# BeerWalk Madrid

Encuentra tu ruta craft en Madrid. Mapa de bares de cerveza artesanal, generador
de rutas a pie y recomendación de estilo según tus gustos.

El mismo código corre en dos formatos:

- **Web** (GitHub Pages) — instalable como PWA, funciona sin conexión.
- **App nativa** (iOS + Android) — mismo HTML/CSS/JS empaquetado con Capacitor,
  con permisos de ubicación en tiempo de ejecución y share nativo.

## Estructura

```
index.html              la app entera (HTML + CSS + JS, sin build)
native.js               puente web <-> nativo (permisos, share, botón atrás)
sw.js                   service worker (solo web)
manifest.webmanifest    manifest de la PWA
icons/                  iconos PNG para PWA (192/512, maskable, apple-touch)
resources/              recursos para la app nativa (1024, splash 2732)
scripts/gen_icons.py    genera todos los iconos sin dependencias
scripts/sync_www.sh     copia lo publicable a www/ para Capacitor
scripts/patch_native.py permisos de ubicación en Info.plist y AndroidManifest
capacitor.config.json   configuración de la app nativa
www/                    espejo de lo publicable (lo genera sync_www.sh)
```

## Web

Publicar en GitHub Pages: sirve la raíz del repo. No hay paso de build.

```sh
python3 scripts/gen_icons.py   # regenerar iconos tras cambiar el diseño
```

## App nativa

Ver [NATIVE.md](NATIVE.md) para el paso a paso completo: requisitos, compilación
y publicación en App Store y Play Store.

Resumen:

```sh
npm install
npm run icons        # resources/ -> iconos iOS y Android
sh scripts/sync_www.sh
npx cap add ios
npx cap add android
python3 scripts/patch_native.py
npx cap sync
npm run open:ios      # compila y abre Xcode
npm run open:android  # compila y abre Android Studio
```

## Estado de la clave de Google

`index.html` lleva incrustada una clave de Google Maps para Places (horarios) y
Directions (ruta por calles). **Hoy esa clave no funciona**, ni en la web ni en
la app nativa:

| API | Respuesta | Efecto |
|---|---|---|
| Directions | `403 PERMISSION_DENIED` | la ruta se dibuja como línea recta discontinua, con tiempos estimados a 5 km/h |
| Places | `403 REQUEST_DENIED` ("You must enable Billing") | los horarios no se muestran |

Google responde igual desde `adavmq13.github.io` que desde un origen no
permitido, así que no es una cuestión de restricciones de dominio: al proyecto
de la clave le falta facturación y tener las APIs activadas. La app no se rompe
porque ambos caminos tienen fallback, pero son dos funciones que hoy no hacen
nada.

Antes de publicar hay que arreglarlo en la consola de Google Cloud:

1. Activar la facturación del proyecto.
2. Habilitar **Maps JavaScript API**, **Places API (New)** y **Routes API**.
3. Restringir la clave por dominio para la web y, si publicas la app, permitir
   también `capacitor://localhost` y `https://localhost`, o crear una clave
   aparte para móvil.

Está detallado en [NATIVE.md](NATIVE.md).

## Licencia de datos

Los datos de locales provienen de Google Places y sus reseñas. Google Places
API tiene condiciones de uso propias y un límite de solicitudes que puede
requerir un plan de pago. Antes de publicar en las tiendas conviene revisarlo.
