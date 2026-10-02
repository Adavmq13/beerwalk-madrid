#!/usr/bin/env python3
"""
Comprueba si la app nativa esta lista para compilar y, si no, dice exactamente
que falta.

No compila nada: solo mira. Sirve para no abrir Xcode y encontrarse con un
error a los cinco minutos.

    python3 scripts/preflight.py

Devuelve 0 si esta todo, 1 si falta algo.
"""
import json
import os
import plistlib
import subprocess
import sys
import xml.dom.minidom

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FALTA, AVISO, OK = "FALTA", "AVISO", "OK"


def linea(estado, texto, detalle=""):
    simbolo = {OK: "  ok  ", AVISO: " aviso", FALTA: " FALTA"}.get(estado, "  ?   ")
    texto_completo = "[%s] %s" % (simbolo, texto)
    if detalle:
        texto_completo += "\n           " + detalle
    print(texto_completo)
    return estado


def run(*args):
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=25)
        return (p.stdout + p.stderr).strip()
    except Exception:
        return ""


def es_dir(p):
    return os.path.isdir(os.path.join(ROOT, p))


def comprobar_herramientas():
    estados = []

    v = run("node", "--version")
    estados.append(linea(OK if v else FALTA,
                        "Node %s" % (v or "no encontrado"),
                        "" if v else "Se instala con: ver NATIVE.md, apartado 1"))

    if es_dir("node_modules"):
        v = run(os.path.join(ROOT, "node_modules", ".bin", "cap"), "--version")
        estados.append(linea(OK if v else FALTA, "Capacitor CLI %s" % (v or "no instalada"),
                            "" if v else "Ejecuta: npm install"))
    else:
        estados.append(linea(FALTA, "Dependencias de npm ausentes", "Ejecuta: npm install"))

    xc = es_dir("/Applications/Xcode.app")
    v = run("xcodebuild", "-version") if xc else ""
    estados.append(linea(OK if xc else FALTA,
                        "Xcode %s" % (v.splitlines()[0] if v else "no instalado"),
                        "" if xc else "Se instala desde la App Store. Ocupa unos 30 GB."))

    sel = run("xcode-select", "-p")
    if xc and not sel:
        estados.append(linea(FALTA, "Xcode no esta seleccionado para la linea de comandos",
                            "Ejecuta: sudo xcode-select -s /Applications/Xcode.app/Contents/Developer"))

    java = run("java", "-version").splitlines()
    tiene_java = bool(java) and "Unable to locate" not in (java[0] if java else "")
    estados.append(linea(OK if tiene_java else FALTA,
                        "Java %s" % (java[0] if tiene_java else "no instalado"),
                        "" if tiene_java else "Android Gradle Plugin 8.13 pide JDK 17 o superior"))
    return estados


def comprobar_ios():
    estados = []
    plist_path = os.path.join(ROOT, "ios", "App", "App", "Info.plist")
    if not os.path.exists(plist_path):
        return [linea(FALTA, "ios/ no esta", "Ejecuta: npx cap add ios")]

    with open(plist_path, "rb") as f:
        p = plistlib.load(f)

    if p.get("NSLocationWhenInUseUsageDescription"):
        estados.append(linea(OK, "Permiso de ubicacion declarado"))
    else:
        estados.append(linea(FALTA, "Falta NSLocationWhenInUseUsageDescription",
                            "iOS cierra la app al pedir la posicion. Ejecuta: python3 scripts/patch_native.py"))

    sobran = [k for k in ("NSPhotoLibraryUsageDescription", "NSCameraUsageDescription",
                          "NSLocationAlwaysAndWhenInUseUsageDescription") if k in p]
    if sobran:
        estados.append(linea(AVISO, "Permisos que la app no usa: %s" % ", ".join(sobran),
                            "Se piden justificarlos en la revision. Ejecuta: python3 scripts/patch_native.py"))
    else:
        estados.append(linea(OK, "Sin permisos sobrantes"))

    # El icono se compara por pixeles, no por bytes ni por peso. El nuestro pesa
    # 11 KB porque es un dibujo plano que comprime muy bien, asi que un umbral de
    # tamano daba falso positivo; y los bytes tampoco valen porque patch_icons.py
    # re-codifica el PNG y el mismo dibujo sale distinto.
    origen = os.path.join(ROOT, "resources", "icon.png")
    icon = os.path.join(ROOT, "ios", "App", "App", "Assets.xcassets",
                        "AppIcon.appiconset", "AppIcon-512@2x.png")
    if not os.path.exists(icon):
        estados.append(linea(FALTA, "No hay AppIcon en el proyecto",
                            "Ejecuta: npx cap add ios"))
    elif not os.path.exists(origen):
        estados.append(linea(AVISO, "No encuentro resources/icon.png para comparar"))
    else:
        try:
            sys.path.insert(0, os.path.join(ROOT, "scripts"))
            from patch_icons import read_png
            wa, ha, pa = read_png(origen)
            wb, hb, pb = read_png(icon)
            iguales = (wa, ha) == (wb, hb) and pa == pb
        except Exception as e:
            iguales = None
            estados.append(linea(AVISO, "No he podido comparar el icono", str(e)))
        if iguales is True:
            estados.append(linea(OK, "El AppIcon es el nuestro (%dx%d)" % (wa, ha)))
        elif iguales is False:
            estados.append(linea(AVISO, "El AppIcon no es el nuestro, sigue el de Capacitor",
                                "Ejecuta: python3 scripts/patch_icons.py"))

    spm = os.path.join(ROOT, "ios", "App", "CapApp-SPM", "Package.swift")
    estados.append(linea(OK if os.path.exists(spm) else AVISO,
                        "Swift Package Manager" if os.path.exists(spm) else "Sin Package.swift",
                        "" if os.path.exists(spm) else "Ejecuta: npx cap sync"))
    return estados


def comprobar_android():
    estados = []
    man = os.path.join(ROOT, "android", "app", "src", "main", "AndroidManifest.xml")
    if not os.path.exists(man):
        return [linea(FALTA, "android/ no esta", "Ejecuta: npx cap add android")]

    with open(man, "r", encoding="utf-8") as f:
        texto = f.read()
    try:
        xml.dom.minidom.parseString(texto)
        estados.append(linea(OK, "AndroidManifest.xml es XML valido"))
    except Exception as e:
        estados.append(linea(FALTA, "AndroidManifest.xml corrupto", str(e)))

    faltan = [p for p in ("ACCESS_FINE_LOCATION", "ACCESS_COARSE_LOCATION")
              if p not in texto]
    if faltan:
        estados.append(linea(FALTA, "Faltan permisos: %s" % ", ".join(faltan),
                            "Ejecuta: python3 scripts/patch_native.py"))
    else:
        estados.append(linea(OK, "Permisos de ubicacion declarados"))

    if "density" not in texto:
        estados.append(linea(FALTA, "Falta 'density' en configChanges",
                            "Sin eso el WebView se recarga al cambiar de densidad y se pierde el mapa"))

    res = os.path.join(ROOT, "android", "app", "src", "main", "res")
    if os.path.isdir(res):
        n = sum(1 for _, _, fs in os.walk(res) for f in fs
                if f.startswith("ic_launcher") and f.endswith(".png"))
        estados.append(linea(OK if n >= 5 else AVISO,
                            "%d iconos de launcher" % n,
                            "" if n >= 5 else "Ejecuta: python3 scripts/patch_icons.py"))
    return estados


def comprobar_contenido():
    estados = []
    for etiqueta, ruta in (("iOS", "ios/App/App/public/index.html"),
                           ("Android", "android/app/src/main/assets/public/index.html")):
        p = os.path.join(ROOT, ruta)
        if not os.path.exists(p):
            estados.append(linea(FALTA, "%s: no hay index.html empaquetado" % etiqueta,
                                "Ejecuta: npm run prepare:native"))
            continue
        with open(p, encoding="utf-8") as f:
            html = f.read()
        import re
        m = re.search(r"^var B=(\[{.*?\}\]);$", html, re.M | re.S)
        if not m:
            estados.append(linea(FALTA, "%s: el dataset no se encontro" % etiqueta))
            continue
        import hashlib
        sha = hashlib.sha256(m.group(1).encode()).hexdigest()[:16]
        json.loads(m.group(1))
        origen = os.path.join(ROOT, "index.html")
        with open(origen, encoding="utf-8") as f:
            mo = re.search(r"^var B=(\[{.*?\}\]);$", f.read(), re.M | re.S)
        sha_o = hashlib.sha256(mo.group(1).encode()).hexdigest()[:16]
        if sha != sha_o:
            estados.append(linea(FALTA, "%s: el dataset empaquetado no coincide con index.html" % etiqueta,
                                "Empaquetado %s, origen %s. Ejecuta: npm run prepare:native" % (sha, sha_o)))
        else:
            estados.append(linea(OK, "%s: dataset correcto (%d locales, sha %s)"
                                 % (etiqueta, len(json.loads(m.group(1))), sha)))
    return estados


def comprobar_identidad():
    estados = []
    try:
        with open(os.path.join(ROOT, "capacitor.config.json"), encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception as e:
        return [linea(FALTA, "capacitor.config.json ilegible", str(e))]

    app_id = cfg.get("appId", "")
    if app_id.endswith(".beerwalk") and "adavmq13" in app_id:
        estados.append(linea(AVISO, "appId %s" % app_id,
                            "Es el marcador de partida. Se puede cambiar AHORA; despues de publicar, no."))
    else:
        estados.append(linea(OK, "appId %s" % app_id))

    for etiqueta, ruta in (("iOS", "ios/App/App/capacitor.config.json"),
                           ("Android", "android/app/src/main/assets/capacitor.config.json")):
        p = os.path.join(ROOT, ruta)
        if not os.path.exists(p):
            estados.append(linea(FALTA, "%s: falta capacitor.config.json" % etiqueta,
                                "Ejecuta: npx cap sync"))
            continue
        with open(p, encoding="utf-8") as f:
            otro = json.load(f)
        if otro.get("appId") != app_id:
            estados.append(linea(FALTA, "%s: appId desincronizado (%s != %s)"
                                % (etiqueta, otro.get("appId"), app_id),
                                "Ejecuta: npx cap sync"))
        else:
            estados.append(linea(OK, "%s: appId sincronizado" % etiqueta))
    return estados


def main():
    print("Comprobacion previa a compilar la app nativa")
    todos = []
    for titulo, fn in (("Cadena de herramientas", comprobar_herramientas),
                       ("Proyecto iOS", comprobar_ios),
                       ("Proyecto Android", comprobar_android),
                       ("Contenido empaquetado", comprobar_contenido),
                       ("Identidad de la app", comprobar_identidad)):
        print("\n== %s ==" % titulo)
        todos += fn()

    faltan = sum(1 for e in todos if e == FALTA)
    avisos = sum(1 for e in todos if e == AVISO)
    print("\n" + "-" * 60)
    if faltan:
        print("Faltan %d cosa(s) y %d aviso(s). Ver arriba." % (faltan, avisos))
        print("Lo que mas se repetira: falta instalar Xcode o Android Studio.")
        return 1
    if avisos:
        print("Todo lo basico esta. %d aviso(s) por mirar." % avisos)
        return 0
    print("Todo listo. Ya puedes abrir Xcode o Android Studio.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
