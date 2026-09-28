#!/usr/bin/env python3
"""
Genera index-standalone.html: el mismo index.html con native.js embebido
dentro, para que el fichero se pueda copiar a un repo sin arrastrar el
script suelto.

El service worker, el manifest y los iconos NO se pueden inlinear: el
navegador los exige como peticiones propias. Si solo copias este fichero,
la web funciona pero deja de ser instalable y pierde el modo offline.
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "index.html")
NATIVE = os.path.join(ROOT, "native.js")
OUT = os.path.join(ROOT, "index-standalone.html")

TAG = '<script src="native.js"></script>'

with open(SRC, encoding="utf-8") as f:
    html = f.read()
with open(NATIVE, encoding="utf-8") as f:
    native = f.read()

if TAG not in html:
    raise SystemExit("No encuentro %s: el index.html ya no carga native.js." % TAG)

# Embebe el contenido literal. native.js no contiene la secuencia de cierre
# de script, asi que se puede meter tal cual.
inlined = "<script>\n/* native.js embebido por scripts/build_standalone.py */\n%s\n</script>" % native.rstrip()

html = html.replace(TAG, inlined, 1)

# En la version monolithica la comprobacion debe tolerar que falte el fichero
# suelto: si alguien lo carga igualmente, native.js gana y no hay conflicto.
with open(OUT, "w", encoding="utf-8") as f:
    f.write(html)

print("index-standalone.html  %d bytes (+%d)" % (len(html), len(html) - os.path.getsize(SRC)))
print("Sigue necesitando para ser instalable:")
for dep in ("manifest.webmanifest", "sw.js", "icons/icon-192.png", "icons/icon-512.png",
            "icons/maskable-192.png", "icons/maskable-512.png", "icons/apple-touch-icon.png"):
    size = os.path.getsize(os.path.join(ROOT, dep)) if os.path.exists(os.path.join(ROOT, dep)) else -1
    print("  %-30s %s" % (dep, ("%d bytes" % size) if size >= 0 else "FALTA"))
