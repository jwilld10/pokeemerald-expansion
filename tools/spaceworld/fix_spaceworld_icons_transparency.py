#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
from collections import deque
from PIL import Image

SRC = Path("graphics/spaceworld/shared_icons")
OUT = SRC / "transparent_32x64"

# tolerance for “background-like” pixels
TOL = 10
MAGENTA = (255, 0, 255)  # temp “transparent marker” color

def close(c, bg):
    return all(abs(int(c[i]) - int(bg[i])) <= TOL for i in range(3))

def floodfill_make_transparent(im: Image.Image) -> Image.Image:
    im = im.convert("RGBA")
    w, h = im.size
    px = im.load()

    bg = px[0, 0]  # RGBA
    q = deque([(0, 0)])
    seen = {(0, 0)}

    while q:
        x, y = q.popleft()
        r, g, b, a = px[x, y]

        if a == 255 and close((r, g, b), bg):
            px[x, y] = (r, g, b, 0)
            for nx, ny in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in seen:
                    seen.add((nx, ny))
                    q.append((nx, ny))
    return im

def rgba_to_png8_with_transparency(im: Image.Image, colors: int = 16) -> Image.Image:
    """
    Convert RGBA -> paletted PNG (mode P) with a transparency index.
    Transparent pixels are first painted MAGENTA, then we quantize,
    find MAGENTA’s palette index, force all transparent pixels to it,
    and mark that index as transparent.
    """
    im = im.convert("RGBA")
    w, h = im.size
    rgba = im.load()

    # RGB image where transparent pixels become MAGENTA
    rgb = Image.new("RGB", (w, h), (0, 0, 0))
    rgb_px = rgb.load()
    for y in range(h):
        for x in range(w):
            r, g, b, a = rgba[x, y]
            rgb_px[x, y] = MAGENTA if a == 0 else (r, g, b)

    # Quantize to <=16 colors (paletted)
    pal = rgb.quantize(colors=colors, method=Image.Quantize.MEDIANCUT)

    palette = pal.getpalette()
    if not palette:
        raise RuntimeError("quantize() produced no palette (unexpected)")

    n_entries = len(palette) // 3  # actual palette size
    best_i = 0
    best_d = 10**18
    for i in range(n_entries):
        pr, pg, pb = palette[3*i:3*i+3]
        d = (pr - MAGENTA[0])**2 + (pg - MAGENTA[1])**2 + (pb - MAGENTA[2])**2
        if d < best_d:
            best_d = d
            best_i = i

    # Force MAGENTA-marked pixels to the chosen transparent index
    pal_px = pal.load()
    for y in range(h):
        for x in range(w):
            if rgb_px[x, y] == MAGENTA:
                pal_px[x, y] = best_i

    pal.info["transparency"] = best_i
    return pal

def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    for p in sorted(SRC.glob("*.png")):
        im0 = Image.open(p).convert("RGBA")

        # icons are 2 frames stacked vertically => 32x64 target
        canvas = Image.new("RGBA", (32, 64), (0, 0, 0, 0))
        canvas.paste(im0, (0, 0))

        canvas = floodfill_make_transparent(canvas)
        pal = rgba_to_png8_with_transparency(canvas, colors=16)

        outp = OUT / p.name
        pal.save(outp, format="PNG", optimize=True)

    # quick sanity check
    test = OUT / "bat.png"
    if test.is_file():
        im = Image.open(test)
        print("bat.png mode:", im.mode, "transparency:", im.info.get("transparency"))
        rgba = im.convert("RGBA")
        coords = [(0,0),(31,0),(0,63),(31,63)]
        print("Corners:", [rgba.getpixel(c) for c in coords])

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
