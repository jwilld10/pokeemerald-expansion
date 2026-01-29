#!/usr/bin/env python3
from PIL import Image
from collections import deque
from pathlib import Path
import argparse

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("png", type=Path)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--black-tol", type=int, default=0, help="Tolerance for black match (0 = exact)")
    args = ap.parse_args()

    p = args.png
    im = Image.open(p).convert("RGBA")
    w, h = im.size
    px = im.load()

    tol = args.black_tol

    def is_black(c):
        r,g,b,a = c
        if a == 0:
            return False
        return (abs(r-0) <= tol and abs(g-0) <= tol and abs(b-0) <= tol)

    # 1) Flood-fill BLACK pixels connected to the edges -> make transparent
    q = deque()
    seen = set()

    for x in range(w):
        q.append((x, 0))
        q.append((x, h-1))
    for y in range(h):
        q.append((0, y))
        q.append((w-1, y))

    removed = 0
    while q:
        x, y = q.popleft()
        if (x, y) in seen:
            continue
        seen.add((x, y))
        c = px[x, y]
        if is_black(c):
            px[x, y] = (0, 0, 0, 0)
            removed += 1
            if x > 0: q.append((x-1, y))
            if x < w-1: q.append((x+1, y))
            if y > 0: q.append((x, y-1))
            if y < h-1: q.append((x, y+1))

    # 2) Find bbox of remaining non-transparent pixels (the real sprite)
    bbox = im.getbbox()  # bbox of non-zero alpha (after we removed black)
    if bbox is None:
        raise SystemExit(f"ERROR: After removing black, image became empty: {p}")

    crop = im.crop(bbox)

    # 3) Paste the sprite centered onto a same-size transparent canvas (no scaling)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    cw, ch = crop.size
    ox = (w - cw) // 2
    oy = (h - ch) // 2
    out.alpha_composite(crop, (ox, oy))

    # 4) Hard alpha: either 0 or 255 only (keeps tools happy)
    out_px = out.load()
    for y in range(h):
        for x in range(w):
            r,g,b,a = out_px[x,y]
            out_px[x,y] = (r,g,b, 0 if a == 0 else 255)

    if args.apply:
        out.save(p)
        print(f"APPLIED: {p} | removed edge-black px={removed} | centered bbox={bbox}")
    else:
        print(f"CHECK: {p} | would remove edge-black px={removed} | would center bbox={bbox}")

if __name__ == "__main__":
    main()
