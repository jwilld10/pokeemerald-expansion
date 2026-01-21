#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
from collections import deque
from PIL import Image

SRC = Path("graphics/spaceworld/shared_icons")
OUT = SRC / "fixed_32x64_png8"
OUT.mkdir(parents=True, exist_ok=True)

TOL = 10
BG = (255, 0, 255)  # magenta (background marker)

def close_rgb(a, b):
    return all(abs(int(a[i]) - int(b[i])) <= TOL for i in range(3))

def floodfill_from_seed(px, w, h, seed, bg0):
    q = deque([seed])
    seen = {seed}
    while q:
        x, y = q.popleft()
        r, g, b, a = px[x, y]
        if close_rgb((r, g, b), bg0):
            px[x, y] = (BG[0], BG[1], BG[2], 255)
            for nx, ny in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in seen:
                    seen.add((nx, ny))
                    q.append((nx, ny))

def floodfill_to_bg(im_rgba: Image.Image) -> Image.Image:
    im = im_rgba.convert("RGBA")
    w, h = im.size
    px = im.load()

    # Sample bg from each corner and floodfill from each corner.
    corners = [(0,0), (w-1,0), (0,h-1), (w-1,h-1)]
    for c in corners:
        bg0 = px[c][0:3]
        floodfill_from_seed(px, w, h, c, bg0)

    return im

def ensure_palette_len(pal_list, entries=256):
    # pal_list is RGB triplets, length should be entries*3
    need = entries * 3
    if pal_list is None:
        pal_list = []
    if len(pal_list) < need:
        pal_list = pal_list + [0] * (need - len(pal_list))
    return pal_list

def force_bg_palette_index0(im_rgba: Image.Image) -> Image.Image:
    # Quantize to <=16 colors, no dithering, RGB input (no alpha)
    pal = im_rgba.convert("RGB").quantize(colors=16, dither=Image.Dither.NONE)

    palette = ensure_palette_len(pal.getpalette(), entries=256)

    def pal_rgb(i):
        return palette[3*i], palette[3*i+1], palette[3*i+2]

    # Find palette entry closest to BG among first 16
    best_i = 0
    best_d = 10**9
    for i in range(16):
        pr, pg, pb = pal_rgb(i)
        d = (pr-BG[0])**2 + (pg-BG[1])**2 + (pb-BG[2])**2
        if d < best_d:
            best_d = d
            best_i = i

    # Put that entry at index 0 (swap if needed)
    if best_i != 0:
        p0 = palette[0:3]
        pi = palette[3*best_i:3*best_i+3]
        palette[0:3] = pi
        palette[3*best_i:3*best_i+3] = p0

        data = bytearray(pal.tobytes())
        for n, v in enumerate(data):
            if v == 0:
                data[n] = best_i
            elif v == best_i:
                data[n] = 0

        pal = Image.frombytes("P", pal.size, bytes(data))

    pal.putpalette(palette)
    return pal

def process_one(p: Path):
    im = Image.open(p).convert("RGBA")

    # Create 32x64 sheet (two 32x32 frames stacked vertically is the engine expectation)
    canvas = Image.new("RGBA", (32, 64), (BG[0], BG[1], BG[2], 255))
    canvas.paste(im, (0, 0))  # NW anchored, matching your existing workflow

    # Make outer background fully BG so it becomes palette index 0
    canvas = floodfill_to_bg(canvas)

    # Convert to paletted PNG8 (<=16 colors), with BG at palette index 0
    pal = force_bg_palette_index0(canvas)

    out = OUT / p.name
    pal.save(out, format="PNG", optimize=False)

def main():
    srcs = sorted(SRC.glob("*.png"))
    if not srcs:
        print(f"No PNGs found in {SRC}")
        return 1
    for p in srcs:
        process_one(p)
    print(f"Wrote {len(list(OUT.glob('*.png')))} icons to {OUT}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
