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

## Mapa y rutas: sin Google

La app no depende de Google Maps en nada. Se quitó por completo:

| Antes (Google) | Ahora |
|---|---|
| Mapa: Leaflet + CARTO | **igual**, nunca fue de Google |
| Rutas por calles: Directions API | **OSRM**, motor libre, sin clave |
| Horarios: Places API | **campo `oh`** en el registro del local, opcional |

Dos motivos:

1. **La clave no funcionaba.** El proyecto de Google Cloud no tenía
   facturación, así que Places y Routes devolvían `403`. La web publicaba
   rutas en línea recta y sin horarios, sin mostrar ningún error.
2. **Los términos del EEE.** Desde el 8 de julio de 2025, para proyectos con
   facturación en el Espacio Económico Europeo (España lo es), Google no
   permite mostrar contenido de Places junto a un mapa que no sea de Google.
   Eso era justo lo que hacía la app: horarios de Places sobre un mapa de CARTO.

OSRM (`router.project-osrm.org`) es un motor de enrutado libre, sin clave y con
CORS abierto. Ojo: ese servidor es de pruebas y su uso previsto es evaluación y
desarrollo, no tráfico real. Si la app cresciera habría que montar una instancia
propia. Si OSRM falla, la app cae a la estimación en línea recta con tiempos a
5 km/h, igual que antes.

### Horarios

Cada local puede llevar un campo `oh` con la sintaxis de OpenStreetMap, y la
ficha lo traduce a "Abierto ahora" / "Cerrado ahora" con la hora de cierre:

```js
{"n": "Beer Station", "oh": "Mo-Fr 12:00-23:00; Sa,Su 12:00-01:00"}
```

Se admiten rangos (`Mo-Fr`), listas (`Mo,We,Fr`), `24/7`, `off` y tramos que
cruzan medianoche. La hora de cierre solo se muestra si el local abre ese día.

### Estilos de cerveza

El quiz calcula un estilo, pero los locales no traen ese dato, así que el botón
del resultado no puede filtrar por estilo: aplica el filtro que el plan sí
sugiere de verdad (una cita → taprooms, una ruta intensa → bar craft) y lo dice en
el aviso.

Para que filtre por estilo de verdad, añade el campo opcional `est` al local con
una de estas siete familias:

| `est` |
|---|
| `IPA / Pale Ale` |
| `Lager / Pilsner` |
| `Wheat Beer` |
| `Sour / Wild` |
| `Stout / Porter` |
| `Strong Ale` |
| `Fruit Beer` |

```js
{"n": "Hopper", "est": "IPA / Pale Ale"}
```

En cuanto algún local lo tenga, el botón pasa a decir "Ver locales de tu estilo" y
filtra por la familia del resultado y sus tres alternativas. Se combina con la
búsqueda y con los demás filtros, y cualquier chip lo limpia.

## Nota sobre los datos

Las coordenadas vienen de geocodificación y son imprecisas: hay 19 pares de
locales a menos de 60 m entre sí. Ahora que las rutas son reales, eso se nota
como tramos de "1 min · 1m" entre paradas contiguas. No se ha tocado el fichero
de datos, pero conviene revisar esas coordenadas si se quiere que las rutas
salgan limpias.
