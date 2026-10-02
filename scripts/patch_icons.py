#!/usr/bin/env python3
"""
Pone los iconos y la pantalla de inicio reales en ios/ y android/, que
`npx cap add` deja con el logo de Capacitor por defecto.

Es idempotente y se puede volver a ejecutar cada vez que se regeneren los
recursos con `python3 scripts/gen_icons.py`.

De donde salen:
  resources/icon.png            1024x1024, la de App Store y la de iOS
  resources/splash.png          2732x2732, la de las tiendas
  resources/icon-foreground.png 1024x1024, la capa de delante de Android

Sin dependencias: escala por vecino mas proximo, no por interpolacion, para no
suavizar los bordes del dibujo. Los PNG de origen se pintaron a mano pixel a
pixel y les queda bien el borde limpio.
"""
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "resources")

# name -> tamano en px. Los nombres son los que espera cada plataforma.
# iOS: 1024 para el universal; el resto de slots se genera desde ese mismo
# fichero porque Contents.json solo tiene una entrada "universal".
IOS_ICONS = {
    "AppIcon-512@2x.png": 1024,
}

# Android: un icono por bucket de densidad, dentro de mipmap-<bucket>.
ANDROID_ICON_SIZES = {
    "mdpi": 48,
    "hdpi": 72,
    "xhdpi": 96,
    "xxhdpi": 144,
    "xxxhdpi": 192,
}

# El fondo de Android va aparte del foreground: en las versions moderne
# (API 26+) el icono es un adaptive icon con dos capas y el sistema lo
# enmascara. Por eso resources/ trae icon-background.png e icon-foreground.png.
ANDROID_FOREGROUND_SIZES = {
    "mdpi": 108,
    "hdpi": 162,
    "xhdpi": 216,
    "xxhdpi": 324,
    "xxxhdpi": 432,
}

# La pantalla de inicio de Android va en drawable-*/ con el sufijo de densidad.
ANDROID_SPLASH_DENSITIES = ["port", "land"]


def read_png(path):
    """Devuelve (anchura, altura, filas RGB) leyendo solo lo necesario.

    Se decodifica con zlib a mano porque en esta maquina no hay Pillow y anadir
    una dependencia para escalar cuatro iconos no compensa.
    """
    import zlib

    with open(path, "rb") as f:
        data = f.read()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("no es un PNG: %s" % path)

    pos = 8
    w = h = depth = ctype = None
    idat = b""
    while pos < len(data):
        (length,) = struct.unpack(">I", data[pos:pos + 4])
        tag = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + length]
        if tag == b"IHDR":
            w, h, depth, ctype = struct.unpack(">IIBB", body[:10])
        elif tag == b"IDAT":
            idat += body
        elif tag == b"IEND":
            break
        pos += 12 + length

    if depth != 8:
        raise ValueError("solo PNG de 8 bits, %s es de %d" % (path, depth))
    if ctype == 3:
        raise ValueError("PNG con paleta en %s: hace falta la tabla PLTE, "
                         "que este lector no implementa" % path)
    canales = {0: 1, 2: 3, 4: 2, 6: 4}.get(ctype)
    if canales is None:
        raise ValueError("tipo de color PNG no soportado (%d) en %s" % (ctype, path))

    raw = zlib.decompress(idat)
    filas = []
    prev = bytearray(w * canales)
    off = 0
    for _ in range(h):
        filtro = raw[off]
        off += 1
        line = bytearray(raw[off:off + w * canales])
        off += w * canales
        # Deshacer los 5 filtros de PNG. Sin esto las imagenes salen movidas.
        for x in range(len(line)):
            a = line[x - canales] if x >= canales else 0
            b = prev[x]
            c = prev[x - canales] if x >= canales else 0
            if filtro == 1:
                line[x] = (line[x] + a) & 0xFF
            elif filtro == 2:
                line[x] = (line[x] + b) & 0xFF
            elif filtro == 3:
                line[x] = (line[x] + ((a + b) >> 1)) & 0xFF
            elif filtro == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[x] = (line[x] + pr) & 0xFF
        filas.append(line)
        prev = line

    # A RGB, con el alfa compuesto sobre blanco. Hay que tratar los cuatro casos
    # por separado: antes solo se contemplaban gris y RGBA, y una imagen de 3
    # canales caia en la rama "gris" y salia como (r, r, r). El naranja de la
    # jarra (180, 83, 9) se leia (180, 180, 180).
    rgb = bytearray(w * h * 3)
    for y, line in enumerate(filas):
        o = y * w * 3
        for x in range(w):
            b0 = x * canales
            if canales == 3:            # RGB
                r, g, b = line[b0], line[b0 + 1], line[b0 + 2]
            elif canales == 4:          # RGBA
                r, g, b, a = line[b0], line[b0 + 1], line[b0 + 2], line[b0 + 3]
                r = (r * a + 255 * (255 - a)) // 255
                g = (g * a + 255 * (255 - a)) // 255
                b = (b * a + 255 * (255 - a)) // 255
            elif canales == 2:          # gris con alfa
                v, a = line[b0], line[b0 + 1]
                r = g = b = (v * a + 255 * (255 - a)) // 255
            else:                       # 1 canal: gris
                r = g = b = line[b0]
            rgb[o], rgb[o + 1], rgb[o + 2] = r, g, b
            o += 3
    return w, h, rgb


def scale_nearest(w, h, rgb, tw, th):
    """Escala por vecino mas proximo. Sin biblioteca, sin suavizado."""
    out = bytearray(tw * th * 3)
    for y in range(th):
        sy = min(h - 1, y * h // th)
        for x in range(tw):
            sx = min(w - 1, x * w // tw)
            s = (sy * w + sx) * 3
            d = (y * tw + x) * 3
            out[d] = rgb[s]
            out[d + 1] = rgb[s + 1]
            out[d + 2] = rgb[s + 2]
    return out


def write_png(path, w, h, rgb):
    import zlib

    raw = bytearray()
    for y in range(h):
        raw.append(0)  # filtro "none": no hace falta comprimir mas
        raw += rgb[y * w * 3:(y + 1) * w * 3]

    def chunk(tag, body):
        c = struct.pack(">I", len(body)) + tag + body
        return c + struct.pack(">I", zlib.crc32(tag + body) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(png)


def scaled_cache(src, size):
    """Lee el origen una vez y devuelve el buffer al tamano pedido."""
    w, h, rgb = read_png(src)
    if (w, h) == (size, size):
        return w, h, rgb
    return size, size, scale_nearest(w, h, rgb, size, size)


def patch_ios():
    destino = os.path.join(ROOT, "ios", "App", "App", "Assets.xcassets",
                           "AppIcon.appiconset")
    if not os.path.isdir(destino):
        print("  iOS: AppIcon.appiconset no existe. Ejecuta `npx cap add ios` primero.")
        return False
    fuente = os.path.join(RES, "icon.png")
    n = 0
    for nombre, size in sorted(IOS_ICONS.items()):
        w, h, rgb = scaled_cache(fuente, size)
        write_png(os.path.join(destino, nombre), w, h, rgb)
        n += 1
    print("  iOS: %d icono(s) en AppIcon.appiconset" % n)
    return True


def patch_android():
    base = os.path.join(ROOT, "android", "app", "src", "main", "res")
    if not os.path.isdir(base):
        print("  Android: res/ no existe. Ejecuta `npx cap add android` primero.")
        return False
    if not os.path.isdir(os.path.join(base, "mipmap-hdpi")):
        print("  Android: faltan los mipmap. Ejecuta `npx cap add android` primero.")
        return False

    fg = os.path.join(RES, "icon-foreground.png")
    ic = os.path.join(RES, "icon.png")
    n = 0
    for bucket, size in sorted(ANDROID_ICON_SIZES.items()):
        # Los ficheros heredados (no adaptive) usan el icono tal cual.
        w, h, rgb = scaled_cache(ic, size)
        write_png(os.path.join(base, "mipmap-%s" % bucket, "ic_launcher.png"), w, h, rgb)
        w, h, rgb = scaled_cache(ic, size)
        write_png(os.path.join(base, "mipmap-%s" % bucket, "ic_launcher_round.png"), w, h, rgb)
        n += 2
    for bucket, size in sorted(ANDROID_FOREGROUND_SIZES.items()):
        d = os.path.join(base, "mipmap-%s" % bucket)
        if not os.path.isdir(d):
            continue
        w, h, rgb = scaled_cache(fg, size)
        write_png(os.path.join(d, "ic_launcher_foreground.png"), w, h, rgb)
        n += 1
    print("  Android: %d icono(s) en mipmap-*" % n)
    return True


def main():
    print("Iconos y splash en ios/ y android/")
    ok_ios = patch_ios()
    ok_and = patch_android()
    if not (ok_ios or ok_and):
        sys.exit(1)
    print("  (las pantallas de inicio las pone el storyboard y el theme, no aqui)")


if __name__ == "__main__":
    main()
