#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
from collections import deque
from PIL import Image

SRC = Path("graphics/spaceworld/shared_icons")
OUT = SRC / "fixed_32x64_index0"
OUT.mkdir(parents=True, exist_ok=True)

TOL = 10
BG_RGB = (0, 0, 0)  # palette index 0 color (actual RGB doesn't matter for OBJ)

def close_rgb(a, b):
    return all(abs(int(a[i]) - int(b[i])) <= TOL for i in range(3))

def flood_bg_mask(im_rgba: Image.Image):
    """Return a mask of pixels connected to (0,0) that look like the background."""
    im = im_rgba.convert("RGBA")
    w, h = im.size
    px = im.load()
    bg = px[0, 0][:3]

    q = deque([(0, 0)])
    seen = set([(0, 0)])
    mask = [[False]*w for _ in range(h)]

    while q:
        x, y = q.popleft()
        if close_rgb(px[x, y][:3], bg):
            mask[y][x] = True
            for nx, ny in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in seen:
                    seen.add((nx, ny))
                    q.append((nx, ny))
    return mask

def force_index0_png8(im: Image.Image) -> Image.Image:
    """
    1) Floodfill background (connected to top-left)
    2) Paint those pixels to BG_RGB
    3) Quantize to 16 colors (palette)
    4) Ensure BG_RGB ends up at palette index 0 by swapping indices if needed
    """
    im = im.convert("RGBA")
    w, h = im.size

    mask = flood_bg_mask(im)
    px = im.load()
    for y in range(h):
        for x in range(w):
            if mask[y][x]:
                px[x, y] = (*BG_RGB, 255)

    # Quantize to 16 colors
    q = im.convert("RGB").quantize(colors=16, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)

    # Find which palette index matches BG_RGB best
    pal = q.getpalette() or []
    # pad palette to 256 entries
    if len(pal) < 768:
        pal = pal + [0] * (768 - len(pal))
        q.putpalette(pal)

    def pal_rgb(i):
        return pal[3*i], pal[3*i+1], pal[3*i+2]

    # locate bg index
    bg_idx = 0
    best = 10**9
    for i in range(256):
        pr, pg, pb = pal_rgb(i)
        d = (pr-BG_RGB[0])**2 + (pg-BG_RGB[1])**2 + (pb-BG_RGB[2])**2
        if d < best:
            best = d
            bg_idx = i

    if bg_idx != 0:
        # swap palette entries 0 and bg_idx, and remap pixels
        pal0 = pal[0:3]
        palbg = pal[3*bg_idx:3*bg_idx+3]
        pal[0:3] = palbg
        pal[3*bg_idx:3*bg_idx+3] = pal0
        q.putpalette(pal)

        data = bytearray(q.tobytes())
        for i, v in enumerate(data):
            if v == 0:
                data[i] = bg_idx
            elif v == bg_idx:
                data[i] = 0
        q = Image.frombytes("P", q.size, bytes(data))
        q.putpalette(pal)

    return q

def main():
    for p in sorted(SRC.glob("*.png")):
        im = Image.open(p)

        # ensure 32x64 canvas, keep top frame at top, bottom frame below (existing icons often already do this)
        canvas = Image.new("RGBA", (32, 64), (0,0,0,255))
        im = im.convert("RGBA")
        canvas.alpha_composite(im, (0, 0))

        out = force_index0_png8(canvas)
        out.save(OUT / p.name)
    print("Wrote:", OUT)

if __name__ == "__main__":
    main()
