#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
from collections import deque
from PIL import Image

SRC = Path("graphics/spaceworld/shared_icons")
OUT = SRC / "fixed_32x64_trns0"
OUT.mkdir(parents=True, exist_ok=True)

TOL = 10

def close_rgb(a, b):
    return all(abs(int(a[i]) - int(b[i])) <= TOL for i in range(3))

def bg_mask(im_rgba: Image.Image):
    """Mask of bg-ish pixels connected to (0,0)."""
    im = im_rgba.convert("RGBA")
    w, h = im.size
    px = im.load()
    bg = px[0,0][:3]
    q = deque([(0,0)])
    seen = {(0,0)}
    m = [[False]*w for _ in range(h)]
    while q:
        x,y = q.popleft()
        if close_rgb(px[x,y][:3], bg):
            m[y][x] = True
            for nx,ny in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                if 0 <= nx < w and 0 <= ny < h and (nx,ny) not in seen:
                    seen.add((nx,ny))
                    q.append((nx,ny))
    return m

def process_one(p: Path):
    im = Image.open(p).convert("RGBA")
    # Ensure 32x64 canvas (icons are 2 frames stacked vertically)
    canvas = Image.new("RGBA", (32,64), (0,0,0,255))
    canvas.alpha_composite(im, (0,0))

    m = bg_mask(canvas)
    w,h = canvas.size
    rgb = canvas.convert("RGB")
    rpx = rgb.load()

    # Build a working image where background pixels are a sentinel color
    # (we'll force them to palette index 0 after quantization)
    SENT = (1, 2, 3)  # unlikely to appear
    for y in range(h):
        for x in range(w):
            if m[y][x]:
                rpx[x,y] = SENT

    # Quantize to 16 colors
    q = rgb.quantize(colors=16, dither=Image.Dither.NONE)

    pal = q.getpalette() or []
    if len(pal) < 768:
        pal = pal + [0]*(768-len(pal))
        q.putpalette(pal)

    def pal_rgb(i):
        return (pal[3*i], pal[3*i+1], pal[3*i+2])

    # Find which palette entry matches SENT best
    best_i = 0
    best_d = 10**9
    for i in range(256):
        pr,pg,pb = pal_rgb(i)
        d = (pr-SENT[0])**2 + (pg-SENT[1])**2 + (pb-SENT[2])**2
        if d < best_d:
            best_d = d
            best_i = i

    # Remap so SENT color becomes index 0 (transparent)
    data = bytearray(q.tobytes())
    if best_i != 0:
        # swap palette entries 0 and best_i
        p0 = pal[0:3]
        ps = pal[3*best_i:3*best_i+3]
        pal[0:3] = ps
        pal[3*best_i:3*best_i+3] = p0

        for k,v in enumerate(data):
            if v == 0:
                data[k] = best_i
            elif v == best_i:
                data[k] = 0

    out = Image.frombytes("P", q.size, bytes(data))
    out.putpalette(pal)
    out.info["transparency"] = 0  # THIS is the key part
    out.save(OUT / p.name)

def main():
    for p in sorted(SRC.glob("*.png")):
        process_one(p)
    print("Wrote:", OUT)

if __name__ == "__main__":
    main()
