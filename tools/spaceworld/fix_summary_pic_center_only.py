#!/usr/bin/env python3
from PIL import Image
import sys
from pathlib import Path

def main(path):
    p = Path(path)
    img = Image.open(p)

    if img.mode != "P":
        raise SystemExit(f"ERROR: {p} is not palette (P) mode")

    w, h = img.size
    pix = img.load()

    # Find bounding box of non-transparent pixels (index != 0)
    xs, ys = [], []
    for y in range(h):
        for x in range(w):
            if pix[x, y] != 0:
                xs.append(x)
                ys.append(y)

    if not xs:
        print(f"SKIP (empty): {p}")
        return

    minx, maxx = min(xs), max(xs)
    miny, maxy = min(ys), max(ys)

    bw = maxx - minx + 1
    bh = maxy - miny + 1

    # Create new transparent canvas
    out = Image.new("P", (64, 64), 0)
    out.putpalette(img.getpalette())

    ox = (64 - bw) // 2
    oy = (64 - bh) // 2

    src = img.crop((minx, miny, maxx + 1, maxy + 1))
    out.paste(src, (ox, oy))

    out.save(p)
    print(f"APPLIED: {p} | centered bbox=({bw}x{bh})")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: fix_summary_pic_center_only.py <image.png>")
        sys.exit(1)
    main(sys.argv[1])
