#!/bin/sh
# Copia el contenido publicable a www/ para que Capacitor lo empaquete.
# El repo sigue sirviendo la web desde la raiz (GitHub Pages); www/ es
# un espejo exacto mas los recursos que solo necesita la app nativa.
set -e
cd "$(dirname "$0")/.."

mkdir -p www/icons

cp index.html native.js manifest.webmanifest sw.js www/
cp icons/*.png www/icons/

echo "www/ sincronizado:"
ls -1 www www/icons | sed 's/^/  /'
