#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import deque
from pathlib import Path
from PIL import Image


def floodfill_bg_mask(im: Image.Image, bg_idx: int) -> list[bool]:
    """Mask pixels connected to any edge that have value bg_idx."""
    w, h = im.size
    pix = im.load()
    q = deque()
    seen = [False] * (w * h)

    def push(x: int, y: int):
        if x < 0 or y < 0 or x >= w or y >= h:
            return
        i = y * w + x
        if seen[i]:
            return
        if pix[x, y] != bg_idx:
            return
        seen[i] = True
        q.append((x, y))

    for x in range(w):
        push(x, 0)
        push(x, h - 1)
    for y in range(h):
        push(0, y)
        push(w - 1, y)

    while q:
        x, y = q.popleft()
        push(x + 1, y)
        push(x - 1, y)
        push(x, y + 1)
        push(x, y - 1)

    return seen


def bbox_of_nonzero(data: list[int], w: int, h: int) -> tuple[int, int, int, int] | None:
    xs, ys = [], []
    for y in range(h):
        row = data[y * w:(y + 1) * w]
        for x, v in enumerate(row):
            if v != 0:
                xs.append(x)
                ys.append(y)
    if not xs:
        return None
    return (min(xs), min(ys), max(xs) + 1, max(ys) + 1)


def find_unused_index(sprite_idxs: set[int], palette_size: int = 16) -> int | None:
    for i in range(palette_size):
        if i not in sprite_idxs:
            return i
    return None


def swap_indices(data: list[int], a: int, b: int) -> None:
    if a == b:
        return
    for i, v in enumerate(data):
        if v == a:
            data[i] = b
        elif v == b:
            data[i] = a


def swap_pal_entry(pal: list[int], ia: int, ib: int) -> None:
    a0, b0 = ia * 3, ib * 3
    pal[a0:a0+3], pal[b0:b0+3] = pal[b0:b0+3], pal[a0:a0+3]


def process_one(path: Path, canvas: int, apply: bool) -> None:
    im = Image.open(path)
    if im.mode != "P":
        raise SystemExit(f"ERROR: {path} is {im.mode}, expected indexed PNG (mode P).")

    w, h = im.size
    if w != canvas or h != canvas:
        raise SystemExit(f"ERROR: {path} is {w}x{h}, expected {canvas}x{canvas}.")

    palette = im.getpalette()
    if palette is None:
        raise SystemExit(f"ERROR: {path} has no palette.")

    pix = im.load()
    corner_idx = pix[0, 0]

    bgmask = floodfill_bg_mask(im, corner_idx)
    data = list(im.getdata())

    # Indices used by the sprite (non-edge-connected background region)
    sprite_idxs = set()
    for i, v in enumerate(data):
        if not bgmask[i]:
            sprite_idxs.add(v)

    # Choose a transparent index not used by sprite so we never erase real pixels.
    trans_idx = find_unused_index(sprite_idxs, palette_size=16)
    if trans_idx is None:
        raise SystemExit(f"ERROR: {path}: sprite uses all 16 indices; no safe transparent index available.")

    # Convert ONLY edge-connected bg pixels to trans_idx
    changed_bg = 0
    for i in range(len(data)):
        if bgmask[i] and data[i] != trans_idx:
            data[i] = trans_idx
            changed_bg += 1

    # Make transparency be index 0 by swapping indices + palette entries
    if trans_idx != 0:
        swap_indices(data, trans_idx, 0)
        swap_pal_entry(palette, trans_idx, 0)

    # Center without resampling: copy indices into new canvas filled with 0
    bbox = bbox_of_nonzero(data, canvas, canvas)
    if bbox is None:
        out = Image.new("P", (canvas, canvas), 0)
        out.putpalette(palette)
    else:
        x0, y0, x1, y1 = bbox
        bw, bh = (x1 - x0), (y1 - y0)
        offx = (canvas - bw) // 2
        offy = (canvas - bh) // 2

        out_data = [0] * (canvas * canvas)
        for y in range(bh):
            for x in range(bw):
                v = data[(y0 + y) * canvas + (x0 + x)]
                if v != 0:
                    out_data[(offy + y) * canvas + (offx + x)] = v

        out = Image.new("P", (canvas, canvas), 0)
        out.putpalette(palette)
        out.putdata(out_data)

    out.info["transparency"] = 0

    if apply:
        out.save(path, optimize=False)
        print(f"APPLIED: {path} | bg_removed_px={changed_bg} | corner_idx={corner_idx} | centered_bbox={bbox}")
    else:
        print(f"WOULD APPLY: {path} | bg_removed_px={changed_bg} | corner_idx={corner_idx} | centered_bbox={bbox}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+", help="PNG(s) to fix (must be 64x64 indexed PNG)")
    ap.add_argument("--canvas", type=int, default=64)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    for p in args.paths:
        process_one(Path(p), args.canvas, args.apply)


if __name__ == "__main__":
    main()
