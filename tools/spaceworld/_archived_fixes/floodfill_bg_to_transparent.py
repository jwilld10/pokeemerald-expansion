#!/usr/bin/env python3
from PIL import Image
from collections import deque
import argparse
from pathlib import Path

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("png", type=Path)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--tol", type=int, default=0, help="Color tolerance (0 = exact)")
    args = ap.parse_args()

    im = Image.open(args.png).convert("RGBA")
    w, h = im.size
    px = im.load()

    # Background color = top-left pixel
    bg = px[0, 0]
    tol = args.tol

    def close(c):
        return (abs(c[0]-bg[0]) <= tol and abs(c[1]-bg[1]) <= tol and abs(c[2]-bg[2]) <= tol and abs(c[3]-bg[3]) <= tol)

    # Flood fill from edges only
    q = deque()
    seen = set()

    # Seed all border pixels
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
        if close(c):
            # make transparent
            px[x, y] = (0, 0, 0, 0)
            removed += 1
            if x > 0: q.append((x-1, y))
            if x < w-1: q.append((x+1, y))
            if y > 0: q.append((x, y-1))
            if y < h-1: q.append((x, y+1))

    # Also: eliminate semi-transparency (gbagfx hates it sometimes)
    for y in range(h):
        for x in range(w):
            r,g,b,a = px[x,y]
            px[x,y] = (r,g,b, 0 if a == 0 else 255)

    if args.apply:
        im.save(args.png)
        print(f"APPLIED: {args.png} (removed {removed} bg pixels)")
    else:
        print(f"CHECK: {args.png} (would remove {removed} bg pixels)")

if __name__ == "__main__":
    main()
