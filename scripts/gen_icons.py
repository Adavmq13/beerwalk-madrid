#!/usr/bin/env python3
"""
Genera los recursos graficos de la app (iconos iOS/Android + splash)
sin dependencias externas: escribe PNG a mano con zlib.

Salida en resources/:
  icon.png                 1024x1024  icono completo (fondo + jarra)
  icon-background.png      1024x1024  fondo solido (#111) para adaptive icon
  icon-foreground.png      1024x1024  solo la jarra, fondo transparente
  splash.png              2732x2732  fondo crema con la jarra centrada
"""
import math
import os
import struct
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "resources")
WEB_ICONS = os.path.join(ROOT, "icons")

INK = (0x11, 0x11, 0x11, 255)
CREAM = (0xF7, 0xF7, 0xF5, 255)
AMBER = (0xD9, 0x77, 0x06, 255)
AMBER_D = (0xB4, 0x53, 0x09, 255)
AMBER_L = (0xF5, 0xB0, 0x3C, 255)
FOAM = (0xFC, 0xFA, 0xF6, 255)
CLEAR = (0, 0, 0, 0)


# ── utilidades de color ────────────────────────────────────────────────
def over(dst, src):
    """Composición 'source-over' de src (RGBA) sobre dst (RGBA)."""
    sa = src[3] / 255.0
    if sa >= 1.0:
        return src
    if sa <= 0.0:
        return dst
    return (
        int(round(src[0] * sa + dst[0] * (1 - sa))),
        int(round(src[1] * sa + dst[1] * (1 - sa))),
        int(round(src[2] * sa + dst[2] * (1 - sa))),
        max(dst[3], src[3]),
    )


def in_rrect(x, y, w, h, r):
    if x < 0 or y < 0 or x > w or y > h:
        return False
    cx = min(max(x, r), w - r)
    cy = min(max(y, r), h - r)
    return (x - cx) ** 2 + (y - cy) ** 2 <= r * r


def in_annulus(x, y, cx, cy, ro, ri):
    d = math.hypot(x - cx, y - cy)
    return ri <= d <= ro


# ── la jarra, en coordenadas normalizadas 0..1 ─────────────────────────
# Geometria centrada horizontalmente: el cuerpo ocupa 0.169..0.659 y el asa
# llega hasta 0.832, de modo que el conjunto queda centrado en u=0.5.
BODY_CX = 0.4135
BODY_TOP = 0.300
BODY_BOT = 0.865
BODY_HW_TOP = 0.215
BODY_HW_BOT = 0.245
HANDLE_CX = 0.7135
HANDLE_CY = 0.545
HANDLE_RO = 0.118
HANDLE_RI = 0.062


def in_body(u, v):
    if not (BODY_TOP <= v <= BODY_BOT):
        return False
    t = (v - BODY_TOP) / (BODY_BOT - BODY_TOP)
    return abs(u - BODY_CX) <= BODY_HW_TOP + (BODY_HW_BOT - BODY_HW_TOP) * t


def in_foam(u, v):
    # banda de espuma con tres lomos cuyas bases caen dentro de la banda,
    # para que la silueta no tenga muescas entre lomos.
    if 0.130 <= u <= 0.700 and 0.195 <= v <= 0.335 and in_rrect(u - 0.130, v - 0.195, 0.570, 0.140, 0.055):
        return True
    for cx, r in ((0.240, 0.090), (0.4135, 0.108), (0.590, 0.090)):
        if (u - cx) ** 2 + (v - 0.195) ** 2 <= r * r:
            return True
    return False


def mug_layers(u, v):
    """Devuelve la lista de (color, predicado) de la jarra en (u, v)."""
    layers = []

    # asa: anillo cuyo lado izquierdo pica el cuerpo y cuyo hueco queda libre
    layers.append((AMBER_D, lambda u, v: in_annulus(u, v, HANDLE_CX, HANDLE_CY, HANDLE_RO, HANDLE_RI)))

    # cuerpo: trapecio ligeramente ensanchado
    layers.append((AMBER_D, in_body))

    # cerveza mas oscura en la base
    layers.append((AMBER_D, lambda u, v: in_body(u, v) and v > 0.760))

    # brillo vertical en el lado izquierdo de la jarra
    layers.append((AMBER_L, lambda u, v: in_body(u, v) and 0.050 <= u - BODY_CX <= 0.105))

    # espuma
    layers.append((FOAM, in_foam))
    return layers


def draw_mug(buf, W, H, box, scale, aa=3):
    """Dibuja la jarra dentro de `box`=(x0, y0, size) con antialias por supersampling."""
    x0, y0, size = box
    for py in range(max(0, int(y0)), min(H, int(y0 + size))):
        for px in range(max(0, int(x0)), min(W, int(x0 + size))):
            acc = [0.0, 0.0, 0.0, 0.0]
            for sy in range(aa):
                for sx in range(aa):
                    u = ((px - x0) + (sx + 0.5) / aa) / scale
                    v = ((py - y0) + (sy + 0.5) / aa) / scale
                    col = CLEAR
                    for color, test in mug_layers(u, v):
                        if test(u, v):
                            col = color
                    acc[0] += col[0] * col[3] / 255.0
                    acc[1] += col[1] * col[3] / 255.0
                    acc[2] += col[2] * col[3] / 255.0
                    acc[3] += col[3]
            n = aa * aa
            alpha = acc[3] / n
            if alpha <= 0.5:
                continue
            # acc[] guarda color*alfa; se des-premultiplica con la suma de alfas
            asum = acc[3] / 255.0
            src = (
                int(round(acc[0] / asum)),
                int(round(acc[1] / asum)),
                int(round(acc[2] / asum)),
                int(round(alpha)),
            )
            i = (py * W + px) * 4
            buf[i:i + 4] = bytes(over(tuple(buf[i:i + 4]), src))


def new_buf(W, H, color):
    return bytearray(bytes(color) * (W * H))


def png_bytes(buf, W, H):
    raw = bytearray()
    stride = W * 4
    for y in range(H):
        raw.append(0)
        raw += buf[y * stride:(y + 1) * stride]

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 6, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    return png


def save(path, buf, W, H):
    data = png_bytes(buf, W, H)
    with open(path, "wb") as f:
        f.write(data)
    print("  %-24s %dx%d  %6.1f KB" % (os.path.basename(path), W, H, len(data) / 1024))


def write_png(path, buf, W, H):
    save(path, buf, W, H)
    return png_bytes(buf, W, H)


def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(WEB_ICONS, exist_ok=True)
    S = 1024

    # icono completo: fondo ink + jarra al 74% (respeta la zona segura maskable)
    buf = new_buf(S, S, INK)
    draw_mug(buf, S, S, (S * 0.13, S * 0.13, S * 0.74), S * 0.74, aa=4)
    write_png(os.path.join(OUT, "icon.png"), buf, S, S)

    # fondo adaptive (Android recorta hasta un 18% por lado)
    write_png(os.path.join(OUT, "icon-background.png"), new_buf(S, S, INK), S, S)

    # primer plano: jarra sola, dentro del 66% central recomendado
    buf = new_buf(S, S, CLEAR)
    draw_mug(buf, S, S, (S * 0.19, S * 0.19, S * 0.62), S * 0.62, aa=4)
    write_png(os.path.join(OUT, "icon-foreground.png"), buf, S, S)

    # splash
    W = H = 2732
    buf = new_buf(W, H, CREAM)
    draw_mug(buf, W, H, (W * 0.5 - 420, H * 0.5 - 470, 840), 840, aa=3)
    write_png(os.path.join(OUT, "splash.png"), buf, W, H)

    # ── iconos web (PWA) ──────────────────────────────────────────────
    # "any"   : jarra al 74%, el navegador la muestra tal cual.
    # "maskable": jarra al 58%, dentro del 80% central que garantiza que
    #             ningun recorte del sistema se coma la silueta.
    print("\nicons web (PWA) -> %s" % os.path.relpath(WEB_ICONS, ROOT))
    for size in (192, 512):
        for maskable, scale, pad in ((False, 0.74, 0.13), (True, 0.58, 0.21)):
            b = new_buf(size, size, INK)
            draw_mug(b, size, size, (size * pad, size * pad, size * scale), size * scale, aa=3)
            name = ("maskable-%d.png" if maskable else "icon-%d.png") % size
            save(os.path.join(WEB_ICONS, name), b, size, size)

    # apple-touch-icon: iOS no soporta transparencia en el icono de inicio
    b = new_buf(180, 180, INK)
    draw_mug(b, 180, 180, (180 * 0.14, 180 * 0.14, 180 * 0.72), 180 * 0.72, aa=4)
    save(os.path.join(WEB_ICONS, "apple-touch-icon.png"), b, 180, 180)


if __name__ == "__main__":
    main()
