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

## 4. La clave de Google Maps

Este es el paso que más gente se salta y luego no entiende.

`index.html` lleva incrustada una clave de Google Maps para dos cosas:

- **Places API** → horarios de apertura (`fetchHours`)
- **Routes API** → la ruta por calles reales (`computeRoutes`)

Antes de nada: **la clave actual no funciona**, ni en la web ni aquí. Google
devuelve `403` en las dos APIs, y el mensaje de Places dice literalmente *"You
must enable Billing on the Google Cloud Project"*. Se comprobó con peticiones
directas a la API: no es un problema de restricciones de dominio, es que al
proyecto le falta facturación y las APIs activadas. En la web actual eso significa
que los horarios no salen y las rutas se dibujan como líneas rectas.

Arreglo, en la consola de Google Cloud:

1. **Activar la facturación** del proyecto.
2. **Habilitar Maps JavaScript API, Places API (New) y Routes API.** Cada una se
   activa por separado; activar una no habilita las otras.
3. **Restringir la clave.** Para la web, el dominio de GitHub Pages. Para la app
   nativa, las peticiones salen de otro origen:

| Plataforma | Origen de las peticiones |
|---|---|
| iOS | `capacitor://localhost` |
| Android | `https://localhost` |

Opciones para las restricciones:

1. **Añadir esos orígenes** a las restricciones HTTP de la clave existente.
2. **Crear una clave nueva** solo para móvil y ponerla en `index.html` en lugar
   de la actual. Más limpio: separas el consumo de la web del de las apps, y si
   la clave móvil se filtra solo afecta a la app.

Para publicar, mejor la segunda.

Aunque la clave falle, la app arranca y el mapa se ve bien (los tiles son de
CARTO, no de Google). Los dos efectos son degradados y silenciosos: los horarios
simplemente no aparecen, y la ruta se dibuja como una línea recta discontinua con
tiempos estimados a 5 km/h. No hay error visible en pantalla, así que conviene
comprobarlo explícitamente al probar.

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

**Los horarios no salen y la ruta va en línea recta.** Es la clave de Google, y
probablemente no por las restricciones de dominio sino por facturación o APIs sin
activar. La sección 4 lo explica. El síntoma es confuso porque la app funciona y
no muestra ningún error.

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
