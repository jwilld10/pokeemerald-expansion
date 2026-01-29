#!/usr/bin/env python3
from __future__ import annotations
from PIL import Image
from collections import deque
from pathlib import Path
import argparse
import sys

def find_white_index(pal: list[int], avoid: set[int]) -> int:
    # pick brightest palette color (max luminance) not in avoid
    best_i = None
    best_l = -1.0
    for i in range(256):
        if i in avoid:
            continue
        r = pal[i*3+0]
        g = pal[i*3+1]
        b = pal[i*3+2]
        # perceived luminance
        l = 0.2126*r + 0.7152*g + 0.0722*b
        if l > best_l:
            best_l = l
            best_i = i
    return 0 if best_i is None else best_i

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("png", type=Path)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    p = args.png
    im = Image.open(p)

    # We expect paletted PNGs at this stage, but handle RGBA just in case
    if im.mode != "P":
        # Convert to P without changing pixels would be impossible safely;
        # so refuse loudly to avoid wrecking sprites.
        print(f"SKIP: {p} (mode={im.mode}, expected P)", file=sys.stderr)
        return 0

    w, h = im.size
    pal = im.getpalette()
    if pal is None or len(pal) < 768:
        print(f"SKIP: {p} (no palette)", file=sys.stderr)
        return 0

    # Determine what counts as transparent:
    # - If tRNS exists, its value is the transparent palette index
    # - Otherwise, treat index 0 as "transparent candidate" only if it never appears inside opaque region;
    #   but to stay safe, if there's no tRNS we refuse (to avoid nuking real pixels).
    trns = im.info.get("transparency", None)
    if trns is None:
        print(f"SKIP: {p} (no transparency chunk; refusing to guess)", file=sys.stderr)
        return 0

    trans_idx = int(trns)

    # Load indices
    px = im.load()

    # Build mask of transparent pixels
    is_trans = [[False]*w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            is_trans[y][x] = (px[x, y] == trans_idx)

    # Flood fill from border to find "outside" transparent regions
    outside = [[False]*w for _ in range(h)]
    q = deque()

    # Seed border transparent pixels
    for x in range(w):
        if is_trans[0][x]: q.append((x, 0))
        if is_trans[h-1][x]: q.append((x, h-1))
    for y in range(h):
        if is_trans[y][0]: q.append((0, y))
        if is_trans[y][w-1]: q.append((w-1, y))

    while q:
        x, y = q.popleft()
        if outside[y][x]:
            continue
        if not is_trans[y][x]:
            continue
        outside[y][x] = True
        if x > 0: q.append((x-1, y))
        if x < w-1: q.append((x+1, y))
        if y > 0: q.append((x, y-1))
        if y < h-1: q.append((x, y+1))

    # Anything transparent that is NOT outside is an enclosed "hole"
    hole_pixels = []
    for y in range(h):
        for x in range(w):
            if is_trans[y][x] and not outside[y][x]:
                hole_pixels.append((x, y))

    if not hole_pixels:
        if args.verbose:
            print(f"OK: {p} (no enclosed holes)")
        return 0

    # Choose a "white-ish" fill index already in palette
    avoid = {trans_idx}
    fill_idx = find_white_index(pal, avoid)

    # If fill_idx accidentally equals trans, abort
    if fill_idx == trans_idx:
        print(f"SKIP: {p} (could not find non-transparent fill index)", file=sys.stderr)
        return 0

    if args.apply:
        for (x, y) in hole_pixels:
            px[x, y] = fill_idx
        # preserve transparency info
        im.save(p, transparency=trans_idx)
        print(f"APPLIED: {p} | filled_hole_px={len(hole_pixels)} | fill_idx={fill_idx} | trans_idx={trans_idx}")
    else:
        print(f"CHECK: {p} | would_fill_hole_px={len(hole_pixels)} | fill_idx={fill_idx} | trans_idx={trans_idx}")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
