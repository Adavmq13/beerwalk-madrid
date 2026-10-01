#!/usr/bin/env python3
"""
Aplica, tras `npx cap add ios` / `npx cap add android`, los cambios que
Capacitor no genera solo:

  iOS      Info.plist  -> textos de permiso de localizacion
  Android  AndroidManifest.xml -> permisos de ubicacion, configChanges

Es idempotente: se puede volver a ejecutar sin duplicar nada.
"""
import os
import plistlib
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── iOS ────────────────────────────────────────────────────────────────
IOS_PLIST = os.path.join(ROOT, "ios", "App", "App", "Info.plist")

# Sin NSLocationWhenInUseUsageDescription iOS mata la app al pedir la posición.
# Es el único permiso que se pide. No se declara NSPhotoLibraryUsageDescription:
# la app no guarda imágenes (native.js solo hace share, portapapeles, ubicación,
# avisos y botón atrás), y un permiso de fotos que no se usa hay que justificarlo
# en la revisión de App Store.
IOS_USAGE = {
    "NSLocationWhenInUseUsageDescription":
        "BeerWalk usa tu ubicacion para mostrarte los bares craft mas cercanos.",
}

# Claves que este script dejaba antes y que no deben estar. Se borran si
# aparecen, para que el script sea autocorrector y no solo aditivo.
IOS_QUITAR = [
    "NSPhotoLibraryUsageDescription",
    "NSPhotoLibraryAddUsageDescription",
    "NSCameraUsageDescription",
    "NSLocationAlwaysAndWhenInUseUsageDescription",
    "NSLocationAlwaysUsageDescription",
]

# SystemBars (plugin de core) exige que el aspecto de la barra lo controle
# el view controller.
IOS_SETTINGS = {
    "UIViewControllerBasedStatusBarAppearance": True,
    "UIStatusBarStyle": "UIStatusBarStyleDefault",
    "UIRequiresFullScreen": True,
}


def patch_ios():
    if not os.path.exists(IOS_PLIST):
        print("  iOS: Info.plist no encontrado. Ejecuta `npx cap add ios` primero.")
        return False

    # Se edita como plist, no con expresiones regulares: el fichero es XML y
    # una regexp mal construida lo deja corrupto.
    with open(IOS_PLIST, "rb") as f:
        plist = plistlib.load(f)

    changed = 0
    for key, value in list(IOS_USAGE.items()) + list(IOS_SETTINGS.items()):
        if plist.get(key) != value:
            plist[key] = value
            changed += 1

    # Permisos que no hacen falta: se eliminan en vez de solo no añadirse, para
    # que quien lo ejecuto con una version anterior del script se quede limpio.
    quitadas = []
    for key in IOS_QUITAR:
        if key in plist:
            del plist[key]
            quitadas.append(key)

    if changed or quitadas:
        with open(IOS_PLIST, "wb") as f:
            plistlib.dump(plist, f, sort_keys=True)
        print("  iOS: Info.plist actualizado (%d claves, %d permisos retirados)"
              % (changed, len(quitadas)))
        for key in quitadas:
            print("       retirado %s: la app no lo usa" % key)
    else:
        print("  iOS: Info.plist ya estaba al dia")
    return True


# ── Android ────────────────────────────────────────────────────────────
ANDROID_MANIFEST = os.path.join(ROOT, "android", "app", "src", "main", "AndroidManifest.xml")

ANDROID_PERMS = [
    "android.permission.ACCESS_COARSE_LOCATION",
    "android.permission.ACCESS_FINE_LOCATION",
]

# Sin `density`, el WebView se recarga al cambiar de densidad y se pierde el
# estado del mapa. Capacitor 8 pide además `navigation`.
CONFIG_CHANGES = (
    "orientation|keyboardHidden|keyboard|screenSize|locale|smallestScreenSize"
    "|screenLayout|uiMode|navigation|density"
)


def patch_android():
    if not os.path.exists(ANDROID_MANIFEST):
        print("  Android: AndroidManifest.xml no encontrado. Ejecuta `npx cap add android` primero.")
        return False

    with open(ANDROID_MANIFEST, "r", encoding="utf-8") as f:
        text = f.read()
    before = text

    # 1. permisos, justo despues de la etiqueta <manifest ...>
    perms = [p for p in ANDROID_PERMS if p not in text]
    if perms:
        m = re.search(r"<manifest\b[^>]*>", text)
        if not m:
            print("  Android: no encuentro la etiqueta <manifest>; revisa a mano.")
            return False
        block = "\n".join('    <uses-permission android:name="%s" />' % p for p in perms)
        text = text[:m.end()] + "\n" + block + text[m.end():]

    # 2. configChanges completo en la activity
    def fix_config(m):
        current = m.group(1)
        if current == CONFIG_CHANGES:
            return m.group(0)
        return 'android:configChanges="%s"' % CONFIG_CHANGES

    text, n = re.subn(r'android:configChanges="([^"]*)"', fix_config, text)

    if text != before:
        with open(ANDROID_MANIFEST, "w", encoding="utf-8") as f:
            f.write(text)
        print("  Android: %d permisos y %d configChanges actualizados" % (len(perms), n))
    else:
        print("  Android: manifest ya estaba al dia")
    return True


def main():
    print("Parches de configuracion nativa")
    ok_ios = patch_ios()
    ok_android = patch_android()
    if not (ok_ios or ok_android):
        sys.exit(1)


if __name__ == "__main__":
    main()
