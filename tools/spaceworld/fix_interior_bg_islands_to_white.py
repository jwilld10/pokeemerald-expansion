#!/usr/bin/env python3
from PIL import Image
from collections import deque
from pathlib import Path
import argparse

def load_gbapal_16(path: Path):
    data = path.read_bytes()
    # .gbapal is 16-bit BGR555 little-endian, usually 16 colors (32 bytes)
    if len(data) < 32:
        raise SystemExit(f"ERROR: {path}: expected >=32 bytes, got {len(data)}")
    cols = []
    for i in range(0, 32, 2):
        v = data[i] | (data[i+1] << 8)
        b = (v & 0x1F)
        g = (v >> 5) & 0x1F
        r = (v >> 10) & 0x1F
        # expand 5-bit to 8-bit
        cols.append((r * 255 // 31, g * 255 // 31, b * 255 // 31))
    return cols

def brightest_non_bg(pal_rgb, bg_rgb):
    # pick the palette color (excluding exact bg) with max brightness
    best = None
    best_score = -1
    for c in pal_rgb:
        if c == bg_rgb:
            continue
        score = c[0] + c[1] + c[2]
        if score > best_score:
            best_score = score
            best = c
    # fallback: if everything equals bg somehow (shouldn't), use pure white
    return best if best is not None else (255, 255, 255)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("png", type=Path)
    ap.add_argument("gbapal", type=Path)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--tol", type=int, default=0, help="RGB tolerance when matching bg (0 exact)")
    args = ap.parse_args()

    im = Image.open(args.png).convert("RGBA")
    w, h = im.size
    px = im.load()

    bg = px[0, 0]  # RGBA
    tol = args.tol

    def close_rgb(c):
        return (abs(c[0]-bg[0]) <= tol and abs(c[1]-bg[1]) <= tol and abs(c[2]-bg[2]) <= tol)

    # 1) Mark which pixels are "bg-colored" and also border-connected (the real background)
    q = deque()
    seen = set()
    border_bg = set()

    for x in range(w):
        q.append((x, 0))
        q.append((x, h-1))
    for y in range(h):
        q.append((0, y))
        q.append((w-1, y))

    while q:
        x, y = q.popleft()
        if (x, y) in seen:
            continue
        seen.add((x, y))
        r, g, b, a = px[x, y]
        if a != 0 and close_rgb((r, g, b)):
            border_bg.add((x, y))
            if x > 0: q.append((x-1, y))
            if x < w-1: q.append((x+1, y))
            if y > 0: q.append((x, y-1))
            if y < h-1: q.append((x, y+1))

    # 2) Any OTHER opaque pixel matching bg color is an "interior island" -> recolor to palette-white
    pal = load_gbapal_16(args.gbapal)
    bg_rgb = (bg[0], bg[1], bg[2])
    target = brightest_non_bg(pal, bg_rgb)

    changed = 0
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a != 0 and close_rgb((r, g, b)) and (x, y) not in border_bg:
                px[x, y] = (target[0], target[1], target[2], 255)
                changed += 1

    if args.apply:
        im.save(args.png)
        print(f"APPLIED: {args.png} | recolored interior-bg pixels={changed} -> {target}")
    else:
        print(f"CHECK: {args.png} | would recolor interior-bg pixels={changed} -> {target}")

if __name__ == "__main__":
    main()
