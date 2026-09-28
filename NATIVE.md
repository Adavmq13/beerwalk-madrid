# BeerWalk Madrid — guía de la app nativa

Todo el HTML, CSS y JS es el mismo que la web. Capacitor lo empaqueta en un
binario nativo, que añade permisos en tiempo de ejecución, share del sistema y
botón atrás.

## 1. Requisitos

| Herramienta | Para qué |
|---|---|
| **Node.js 22+** | CLI de Capacitor 8 |
| **Xcode 26+** | compilar iOS (desde la App Store) |
| **Android Studio Otter (2025.2.1)+** | compilar Android, incluye el SDK y Java 21 |
| **CocoaPods** | solo si generas iOS con el gestor de paquetes CocoaPods |

El gestor de paquetes de iOS lo decide el CLI al crear la plataforma. Por defecto
usa Swift Package Manager y no necesitas CocoaPods; si lo prefieres:

```sh
npx cap add ios --packagemanager CocoaPods
```

Comprobar antes de seguir:

```sh
node -v
npx cap --version
xcodebuild -version
java -version
```

Para firmar hace falta una **cuenta de Apple Developer** (99 USD/año) y una de
**Google Play** (25 USD, una vez). `es.adavmq13.beerwalk` es solo un marcador:
cámbialo en `capacitor.config.json` por algo que te pertenezca, por ejemplo
`es.tuempresa.beerwalk`. El bundle id no se puede cambiar después de publicar.

## 2. Preparar el proyecto

```sh
npm install
npm run icons        # resources/ -> iconos que usa la app nativa
sh scripts/sync_www.sh
```

`scripts/gen_icons.py` no necesita Node ni ImageMagick: escribe los PNG a mano con
`zlib`. Si cambias el diseño de la jarra, edita `mug_layers()` y vuelve a lanzarlo.

`npm run icons` es un atajo al script de Python. Si prefieres no depender de
Python, `npx @capacitor/assets generate --iconBackgroundColor '#111111'` hace lo
mismo leyendo los PNG de `resources/`.

## 3. Crear las plataformas

```sh
npx cap add ios
npx cap add android
python3 scripts/patch_native.py
npx cap sync
```

`patch_native.py` hace lo que Capacitor no genera solo:

- **`Info.plist`** — `NSLocationWhenInUseUsageDescription`. Sin este texto iOS
  cierra la app en cuanto pides la posición. También
  `UIViewControllerBasedStatusBarAppearance`, que el plugin `SystemBars` de core
  necesita para poder controlar el aspecto de la barra.
- **`AndroidManifest.xml`** — permisos `ACCESS_FINE_LOCATION` y
  `ACCESS_COARSE_LOCATION`, y `density` en `configChanges` de la activity. Sin
  `density` el WebView se recarga al cambiar de densidad y se pierde el estado
  del mapa.

El script edita el `Info.plist` con `plistlib`, no con expresiones regulares, así
que no puede dejar el XML corrupto. Es idempotente: reejecutarlo no duplica nada.

## 4. Google Maps: fuera de la app

No hay nada que configurar. Google se elimino del proyecto.

Antes la app usaba dos APIs sueltas, no el mapa:

- **Places API** -> horarios de apertura (`fetchHours`)
- **Routes API** -> el trazado de la ruta (`computeRoutes`)

El mapa siempre fue Leaflet con teselas de CARTO. No necesita clave, ni
facturacion, ni cuenta, y funciona dentro de la app nativa sin cambios.

Las dos APIs de Google se quitaron por dos motivos:

1. **No funcionaban.** El proyecto de Google Cloud no tenia facturacion, asi que
   ambas devolvian `403`; el mensaje de Places decia *"You must enable Billing on
   the Google Cloud Project"*. El efecto era silencioso: la web publicaba rutas
   en linea recta y sin horarios, sin error visible.
2. **Los terminos del EEE.** Desde el 8 de julio de 2025, un proyecto con
   facturacion en el Espacio Economico Europeo (Espana lo es) no puede mostrar
   contenido de Places junto a un mapa que no sea de Google. La app hacia justo
   eso: horarios de Places sobre un mapa de CARTO.

Los horarios ahora salen de un campo `oh` opcional en el registro de cada local,
en sintaxis de OpenStreetMap. Ver el README.

### Si algun dia quieres volver a Google

No lo recomiendo, pero para que conste: la via que cumple los terminos del EEE
es usar **el mapa de Google**, no el de CARTO, junto con el Places UI Kit. Eso
cambia el aspecto del mapa por completo. Y cargar Google Maps JS dentro de una
app nativa va ademas contra los terminos de Google para iOS, asi que en la
tienda de apps no valdria.

### Rutas: OSRM

El trazado viene de `router.project-osrm.org`, que es un servidor publico de
demostracion. Su uso previsto es evaluacion y desarrollo, no trafico real, y no
tiene SLA ni garantia de disponibilidad.

Para un proyecto personal o con pocos usuarios aguanta. Si la app creciera, lo
correcto seria montarlo en una maquina propia y cambiar la URL dentro de
`generateRoute()`.

Cuando OSRM no responde la app no se rompe: cae a la estimacion en linea recta
con tiempos a 5 km/h y lo avisa con el texto "Estimaci\u00f3n de tiempos". La
peticion lleva un `AbortController` con 8 s de timeout, asi que tampoco se queda
colgada si el servidor deja de responder.


## 5. Zonas seguras y notch

Los elementos fijos (header, píldoras inferiores, hojas) se reajustan con los
tokens `--sat/--sab/--sal/--sar`, definidos al final de la hoja de estilos de
`index.html`. En el navegador valen 0, así que la web no cambia. En la app
resuelven al inset real del dispositivo.

En Android, `env(safe-area-inset-*)` no es fiable en WebView < 140. Por eso el
config usa `SystemBars.insetsHandling: "css"`, que hace que Capacitor inyecte
`--safe-area-inset-*` con los valores correctos, y los tokens los leen con
`var(--safe-area-inset-top, env(safe-area-inset-top, 0px))`: primero la variable
de Capacitor, y si no existe, `env()`. Así funciona en las dos plataformas.

## 6. Compilar y probar

```sh
npm run open:ios        # abre Xcode
npm run open:android    # abre Android Studio
```

Desde Xcode, *Product → Run* con un simulador de iPhone. Desde Android Studio, el
botón ▶ con un emulador. `npx cap run ios` / `run android` hacen las dos cosas
desde la terminal.

Para probar la ubicación real hace falta un dispositivo físico: los simuladores
devuelven una posición fija (Apple Creek en el simulador de iOS) que no sirve
para "bares cerca de mí" en Madrid.

Después de cada cambio en `index.html`:

```sh
sh scripts/sync_www.sh && npx cap sync
```

## 7. Firmar y publicar

### Android (Play Store)

1. Android Studio → *Build → Generate Signed App Bundle / APK*.
2. Crea un keystore y guárdalo **fuera del repo**. Sin él no podrás actualizar
   la app; si lo pierdes, tienes que crear otra entrada en Play con otro
   `applicationId`.
3. Sube el `.aab` a la consola de Play.
4. Rellena la ficha: nombre, iconos, capturas de móvil, descripción, categoría
   de contenido y el aviso de privacidad obligatorio.

Objetivo recomendado: `compileSdk 36`, `minSdk 24`, firmado con la misma clave
en todas las actualizaciones.

### iOS (App Store)

1. Xcode → *Signing & Capabilities* → tu equipo de Apple Developer.
2. *Product → Archive* → *Distribute App* → App Store Connect.
3. Sube las capturas: iPhone 6.7" y 5.5" son obligatorias.

## 8. Actualizar la app

Cambias `index.html`, y:

```sh
sh scripts/sync_www.sh && npx cap sync
```

En iOS hay que subir un build nuevo a App Store Connect en cada versión
publicada: el binario no se auto-actualiza, así que los usuarios tienen que
instalar la actualización. Los binarios firmados caducan a los 30 días para
distribución en tienda; si mantienes la build más de eso, firmará con una
certificación de desarrollo y no llegará a usuarios reales.

## Problemas frecuentes

**iOS cierra la app al pedir la ubicación.** Falta
`NSLocationWhenInUseUsageDescription`. Ejecuta `python3 scripts/patch_native.py`.

**La ruta sale en línea recta y pone "Estimación de tiempos".** OSRM no ha
respondido. Puede ser que el servidor de demostración esté saturado. Comprueba
la URL a mano; si responde, es un problema de red del dispositivo. La app sigue
funcionando, solo pierde el trazado por calles.

**Un local dice "Cerrado ahora" pero el bar está abierto.** No consulta ningún
servicio: lee el campo `oh` del registro. Si no existe, no muestra nada. Si
existe y está mal escrito, se interpreta mal. La sintaxis está en el README.

**`npx cap sync` no copia los cambios.** `webDir` es `www/`, no la raíz. Ejecuta
`sh scripts/sync_www.sh` antes de sincronizar. Olvidar este paso es el fallo más
común.

**Android: el botón atrás cierra la app en vez de la hoja abierta.** El enganche
está al final de `index.html`, en `window.BW.bindBackButton`. Comprueba que
`native.js` se carga antes que el resto del script.

**El splash dura milisegundos o no aparece.** Ajusta
`SplashScreen.launchShowDuration` en `capacitor.config.json` y repite
`npx cap sync`.

**En Android el header queda bajo la barra de estado.** `SystemBars.hidden` debe
ser `false` y `insetsHandling: "css"`. Comprueba también que los tokens
`--sat/--sab` siguen al final de la hoja de estilos: si alguien los mueve arriba,
las reglas base de cada elemento fijo los pisan en la cascada.
