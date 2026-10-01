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

## Enlaces: web, red social u otro

El chip decía "Con web" y metía 18 enlaces que eran solo un Instagram, más un
Facebook, un WhatsApp de reservas y un acortador. Prometía web y no cumplía.

Ahora los enlaces se clasifican por **dominio**, no buscando subcadenas en la
URL (con `indexOf("t.co")`, "wanderlus**t.co**m" contaba como acortador):

| Tipo | Locales | Chip |
|---|---|---|
| Web de verdad | 92 | "Con web" |
| Instagram | 15 | "📷 Con redes" |
| Facebook | 3 | "📷 Con redes" |
| WhatsApp | 1 | "📷 Con redes" |
| Acortador (bit.ly → un PDF) | 1 | — |
| Sin enlace | 28 | — |

Los dos chips son excluyentes: un local tiene un solo enlace, así que activar
uno desactiva el otro. Antes, activar los dos daba un 0 sin explicación.

En la ficha, el botón y el campo de datos dicen lo que son: "📷 Instagram",
"💬 WhatsApp", "🔗 Enlace". Y los 5 puntos de web del score solo se conceden
con una web real, no con un Instagram.

## El Craft Score

Puntuación de 0 a 99 con cuatro pesos: **55** por la nota ajustada, **20** por
volumen de reseñas, **20** por el tipo de local y **5** por tener web.

La nota se ajusta hacia la media del conjunto en proporción a cuántas reseñas
hay. Es la forma estándar de no fiarse de muestras pequeñas:

```
ajustada = (nota × reseñas + media_global × 60) / (reseñas + 60)
```

Con los datos actuales la media global es 4,575. La diferencia se nota:

| Local | Nota | Reseñas | Ajustada | Score |
|---|---|---|---|---|
| WHISKY CLUB MADRID | 5,0 | 540 | 4,96 | **95** |
| Cervecería Dichosita | 5,0 | 363 | 4,94 | 88 |
| Cerveza El Lobo | 5,0 | **1** | 4,58 | **60** |

Un 5,0 con una sola reseña no es lo mismo que un 5,0 con 540, y el score ya no
los trata igual. Antes ambos daban 85 y el texto decía "rating 5.0" sin más.

Antes el score salía con 10 valores distintos para 140 locales y 30 empataban.
Ahora son 37 valores y el empate máximo es de 10.

Las etiquetas ("Imprescindible craft", "Muy recomendable", "Buena opción",
"Pendiente de validar") tienen umbrales 88 / 75 / 62, ajustados a la
distribución real, que va de 52 a 95.

## Fecha de los datos

Los 132 locales vienen de un volcado de Google Places. El fichero se subió al
repo el **15 de mayo de 2026** y el dataset no se ha vuelto a tocar desde
entonces, así que esa es la fecha de los datos. Es una cota superior: el volcado
pudo hacerse unos días antes.

Los 8 locales que se retiraron el 1 de octubre de 2026 son una decisión de
alcance posterior, no un cambio en los datos: conservan la fecha de mayo.

Sin esa fecha, la app presenta con la misma seguridad un bar abierto hoy y uno
que cerró en junio. Ahora cada ficha lo dice en el bloque de datos, y a partir
de un año añade un aviso:

> ⚠ Datos de mayo de 2026. Puede que el local haya cerrado o cambiado desde
> entonces.

Cada local puede llevar su propio campo `v` con la fecha en que lo revisaste a
mano. Acepta ISO (`"2026-10"`) o el mes con letra (`"2026-oct"`), y entonces la
ficha dice "Revisado" en vez de "Datos de":

```js
{"n": "Hopper", "v": "2026-10"}
```

El aviso depende solo de la edad, no de que tenga `v`: un local revisado en
enero de 2024 tiene 33 meses y también avisa.

## Alcance: 132 locales, y por qué no son 140

Ocho locales se retiraron de la selección el 1 de octubre de 2026. Cada uno salió
por una razón comprobada, no por una sospecha:

**Cinco no son de cerveza.** Se verificó contra sus propias webs:

| # | Local | Qué dice su web |
|---|---|---|
| 13 | VinoPremier | "Tienda online de vinos, cervezas, destilados". E-commerce, sin sitio al que ir |
| 35 | Bandida Tapas & Cocktail Bar | "Tapas & Cocktail Bar". **0 menciones de cerveza o craft** en 3.922 palabras |
| 57 | Fat Cats Cocktail House | "Coctelería clandestina". **0 menciones de cerveza o craft** |
| 69 | Madrid & Darracott | "Tienda de vinos en Madrid, eventos, catas". Es vino |
| 115 | CERVETRI Cervezas Online | "Tienda comprar cervezas online". E-commerce, sin sitio al que ir |

**Tres están fuera del ámbito**, que es la Comunidad de Madrid:

| # | Local | Dónde |
|---|---|---|
| 74 | OKasional Beer | Barcelona (41.3823, 2.1625) |
| 118 | BrewPub Rooftop | Usaquén, Bogotá, Colombia |
| 137 | Hopa Beer Denda | Donostia / San Sebastián (43.3228, −1.9738) |

Estos tres no son un error de captura: los datos son correctos, el problema es
de alcance. Un generador de rutas que trabaja con radios de 800 m no les saca
ningún partido.

### Tres que se sospecharon y se quedaron

La revisión por nombre marcó a tres que sí son de cerveza. Se quedan:

| # | Local | Por qué se queda |
|---|---|---|
| 9 | Brew Wild Pizza Bar | Su web: *"Pizza y Cervezas Artesanas"*, *"increíble selección de cervezas artesanales"* |
| 46 | Moraima Vinateros | Su web es **"Cervecerías Moraima"**, 3 menciones de cerveza y 0 de vino. El nombre viene de la calle, Camino de los Vinateros |
| 127 | LUIGIS | El nombre dice *"cocktails tapas & craft beers"* |

### Un apunte sobre las categorías

**#35 Bandida y #57 Fat Cats estaban clasificados como "Bar craft beer"** y son
coctelerías. Eso no viene de la captura sino de la categoría que asignó Google
Places, que a veces se equivoca. Si algún día se reimporta el volcado, conviene
revisar las categorías con el mismo método: leer la web del local, no su nombre.

### Los que se dejan, aunque no sean del centro

Siete locales están en la corona (Valdemoro, Alcalá de Henares, Bustarviejo,
Cabanillas de la Sierra). **Se quedan**: son alcanzables a pie o en transporte,
el generador de rutas los funciona, y para una selección de cerveza de la región
tienen sentido. El límite que se ha trazado es la Comunidad, no el municipio.

Los ocho retirados siguen en el historial de git, por si el ámbito cambia.

## Nota sobre los datos

Las coordenadas vienen de geocodificación y son imprecisas: hay 16 pares de
locales a menos de 60 m entre sí. **En una versión anterior eso producía tramos
de "1 min · 1m" entre paradas contiguas**, porque el generador cogía dos locales
a 40 m y los ponía seguidos.

Ahora no pasa: `generateRoute()` aplica un mínimo de 120 m por tramo
(`MIN_LEG`, en km), así que un local demasiado cerca se salta y se coge el
siguiente. Hay una consecuencia honesta de esto, y la app la dice en vez de
callarse: **la selección está muy concentrada**. En Malasana hay 22 locales a
menos de 800 m; en Retiro, **1**; en Chamberí, 2. Si pides 5 paradas desde
Retiro, solo te puedes dar 1, y el resultado lleva un aviso que lo explica.

Zonas con selección de sobra: Malasana, Chueca, Lavapiés, Centro, Malasaña-
Chueca, Ríos Rosas, Retiro-Chueca. Zonas flojas: Retiro (salvo Fogg Bar),
Chamberí, Vallecas, Carabanchel, Tetuán.

El fichero de datos no se ha tocado, así que las coordenadas siguen siendo las
que son. Si algún día se quieren rutas más limpias, el sitio a arreglar es el
geocodificado, no el generador.
