#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
from collections import deque
from PIL import Image

SRC = Path("graphics/spaceworld/shared_icons")
OUT = SRC / "fixed_32x64_index0"
OUT.mkdir(parents=True, exist_ok=True)

BG = (255, 0, 255)  # magenta, should become palette index 0
TOL = 10

def close_rgb(a, b):
    return all(abs(int(a[i]) - int(b[i])) <= TOL for i in range(3))

def bg_connected_mask(im_rgba: Image.Image):
    im = im_rgba.convert("RGBA")
    w, h = im.size
    px = im.load()
    bg = px[0, 0][:3]
    q = deque([(0, 0)])
    seen = {(0, 0)}
    mask = [[False] * w for _ in range(h)]
    while q:
        x, y = q.popleft()
        if close_rgb(px[x, y][:3], bg):
            mask[y][x] = True
            for nx, ny in ((x+1,y),(x-1,y),(x,y+1),(x,y-1)):
                if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in seen:
                    seen.add((nx, ny))
                    q.append((nx, ny))
    return mask

def swap_palette_index0(pal_img: Image.Image, desired_rgb=(255, 0, 255)) -> Image.Image:
    assert pal_img.mode == "P"
    pal = pal_img.getpalette() or []
    n_entries = len(pal) // 3
    if n_entries == 0:
        return pal_img

    def pal_rgb(i):
        return (pal[3*i], pal[3*i+1], pal[3*i+2])

    best_i, best_d = 0, 10**18
    for i in range(n_entries):
        r, g, b = pal_rgb(i)
        dr, dg, db = r - desired_rgb[0], g - desired_rgb[1], b - desired_rgb[2]
        d = dr*dr + dg*dg + db*db
        if d < best_d:
            best_d, best_i = d, i

    if best_i == 0:
        return pal_img

    data = bytearray(pal_img.tobytes())
    for j, v in enumerate(data):
        if v == 0:
            data[j] = best_i
        elif v == best_i:
            data[j] = 0

    for k in range(3):
        pal[3*0 + k], pal[3*best_i + k] = pal[3*best_i + k], pal[3*0 + k]

    out = Image.frombytes("P", pal_img.size, bytes(data))
    out.putpalette(pal)
    return out

def make_canvas_from_source(src_path: Path) -> Image.Image:
    im = Image.open(src_path).convert("RGBA")
    w, h = im.size

    canvas = Image.new("RGBA", (32, 64), BG + (255,))

    if (w, h) == (16, 32):
        f0 = im.crop((0, 0, 16, 16))
        f1 = im.crop((0, 16, 16, 32))
    elif (w, h) == (32, 64):
        f0 = im.crop((0, 0, 32, 32))
        f1 = im.crop((0, 32, 32, 64))
    elif (w, h) == (32, 32):
        f0 = im
        f1 = im.copy()
    else:
        f0 = im.resize((32, 32), Image.NEAREST)
        f1 = f0.copy()

    canvas.alpha_composite(f0, (8, 8))
    canvas.alpha_composite(f1, (8, 40))

    mask = bg_connected_mask(canvas)
    px = canvas.load()
    for y in range(64):
        for x in range(32):
            if mask[y][x]:
                px[x, y] = BG + (255,)

    return canvas

def to_png8_index0(canvas_rgba: Image.Image) -> Image.Image:
    flat = Image.new("RGBA", canvas_rgba.size, BG + (255,))
    flat.alpha_composite(canvas_rgba)

    pal = flat.quantize(colors=16, method=Image.FASTOCTREE, dither=Image.Dither.NONE)
    pal = swap_palette_index0(pal, BG)
    pal.info["transparency"] = 0
    return pal

def main():
    for p in sorted(SRC.glob("*.png")):
        if p.name.startswith(("fixed_", "transparent_")):
            continue
        canvas = make_canvas_from_source(p)
        out = to_png8_index0(canvas)
        out.save(OUT / p.name, optimize=True)

    print("Wrote:", OUT)

if __name__ == "__main__":
    main()
