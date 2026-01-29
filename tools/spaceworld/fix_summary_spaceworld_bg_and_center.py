#!/usr/bin/env python3
from __future__ import annotations
from collections import deque
from dataclasses import dataclass
from pathlib import Path
import argparse
import sys
from PIL import Image

@dataclass
class Result:
    changed: bool
    bg_to_trans_pixels: int
    bbox: tuple[int,int,int,int] | None
    note: str = ""

def count_border(px, w, h):
    cnt = {}
    total = 0
    def add(x,y):
        nonlocal total
        v = px[x,y]
        cnt[v] = cnt.get(v,0)+1
        total += 1
    for x in range(w):
        add(x,0); add(x,h-1)
    for y in range(h):
        add(0,y); add(w-1,y)
    return cnt, total

def most_common(cnt: dict[int,int]) -> int:
    return max(cnt.items(), key=lambda kv: kv[1])[0] if cnt else 0

def sample_inward_seeds(px, w, h, trans_idx=0):
    """
    For each x on top/bottom, walk inward until non-transparent -> seed.
    For each y on left/right, walk inward until non-transparent -> seed.
    This catches an “inner box” separated from the true border by transparency.
    """
    seeds = []
    vals = []
    # top and bottom
    for x in range(w):
        for y in range(h):
            v = px[x,y]
            if v != trans_idx:
                seeds.append((x,y))
                vals.append(v)
                break
        for y in range(h-1, -1, -1):
            v = px[x,y]
            if v != trans_idx:
                seeds.append((x,y))
                vals.append(v)
                break
    # left and right
    for y in range(h):
        for x in range(w):
            v = px[x,y]
            if v != trans_idx:
                seeds.append((x,y))
                vals.append(v)
                break
        for x in range(w-1, -1, -1):
            v = px[x,y]
            if v != trans_idx:
                seeds.append((x,y))
                vals.append(v)
                break

    # choose most common sampled value
    cnt = {}
    for v in vals:
        cnt[v] = cnt.get(v,0)+1
    bg_idx = most_common(cnt) if cnt else trans_idx

    # keep only seeds that match the chosen bg_idx
    seeds = [(x,y) for (x,y),v in zip(seeds, vals) if v == bg_idx]
    return bg_idx, seeds

def floodfill_from_seeds(px, w, h, bg_idx, seeds):
    q = deque()
    seen = [[False]*w for _ in range(h)]
    def push(x,y):
        if 0 <= x < w and 0 <= y < h and not seen[y][x] and px[x,y] == bg_idx:
            seen[y][x] = True
            q.append((x,y))
    for (x,y) in seeds:
        push(x,y)
    while q:
        x,y = q.popleft()
        push(x+1,y); push(x-1,y); push(x,y+1); push(x,y-1)
    return seen

def bbox_of_foreground(mask_bg, w, h):
    xs = []
    ys = []
    for y in range(h):
        row = mask_bg[y]
        for x in range(w):
            if not row[x]:
                xs.append(x); ys.append(y)
    if not xs:
        return None
    return (min(xs), min(ys), max(xs)+1, max(ys)+1)

def ensure_transparent_index0(imP: Image.Image, mask_bg, bg_idx):
    w,h = imP.size
    px = imP.load()

    pal = imP.getpalette()
    cols = [(pal[i], pal[i+1], pal[i+2]) for i in range(0, 16*3, 3)]
    bg_rgb = cols[bg_idx]

    # swap bg_idx -> 0 if needed
    if bg_idx != 0:
        cols[0], cols[bg_idx] = cols[bg_idx], cols[0]
        for y in range(h):
            for x in range(w):
                v = px[x,y]
                if v == 0:
                    px[x,y] = bg_idx
                elif v == bg_idx:
                    px[x,y] = 0
        bg_idx = 0

    # set background pixels to 0
    bg_to_trans = 0
    for y in range(h):
        for x in range(w):
            if mask_bg[y][x] and px[x,y] != 0:
                px[x,y] = 0
                bg_to_trans += 1

    # detect interior foreground using 0 (hole risk)
    interior_uses_0 = 0
    for y in range(h):
        for x in range(w):
            if not mask_bg[y][x] and px[x,y] == 0:
                interior_uses_0 += 1

    if interior_uses_0 > 0:
        used = set()
        for y in range(h):
            for x in range(w):
                used.add(px[x,y])
        free = None
        for i in range(1,16):
            if i not in used:
                free = i
                break
        if free is None:
            free = 15
        cols[free] = bg_rgb
        for y in range(h):
            for x in range(w):
                if not mask_bg[y][x] and px[x,y] == 0:
                    px[x,y] = free

    outpal = []
    for (r,g,b) in cols:
        outpal.extend([r,g,b])
    outpal.extend([0]*(768-len(outpal)))
    imP.putpalette(outpal)

    return bg_to_trans, interior_uses_0

def center_foreground(imP: Image.Image, mask_bg):
    w,h = imP.size
    bb = bbox_of_foreground(mask_bg, w, h)
    if bb is None:
        return imP, None, False
    x0,y0,x1,y1 = bb
    fw = x1-x0
    fh = y1-y0
    crop = imP.crop((x0,y0,x1,y1))
    new = Image.new("P", (64,64), 0)
    new.putpalette(imP.getpalette())
    ox = (64 - fw)//2
    oy = (64 - fh)//2
    new.paste(crop, (ox,oy))
    return new, bb, True

def process(path: Path, apply: bool) -> Result:
    im = Image.open(path)
    if im.mode != "P" or im.size != (64,64):
        return Result(False, 0, None, note=f"skip: not P/64x64 (mode={im.mode} size={im.size})")

    px = im.load()
    w,h = im.size

    # First try classic border majority
    cnt, total = count_border(px, w, h)
    border_bg = most_common(cnt)
    border_trans_frac = cnt.get(0,0) / total if total else 1.0

    # If border is mostly transparent, pick bg by sampling inward
    if border_trans_frac > 0.80:
        bg_idx, seeds = sample_inward_seeds(px, w, h, trans_idx=0)
        mask_bg = floodfill_from_seeds(px, w, h, bg_idx, seeds)
        note_seed = f"inward_bg={bg_idx} seeds={len(seeds)}"
    else:
        # floodfill from true edges matching border_bg
        seeds = []
        for x in range(w):
            if px[x,0] == border_bg: seeds.append((x,0))
            if px[x,h-1] == border_bg: seeds.append((x,h-1))
        for y in range(h):
            if px[0,y] == border_bg: seeds.append((0,y))
            if px[w-1,y] == border_bg: seeds.append((w-1,y))
        mask_bg = floodfill_from_seeds(px, w, h, border_bg, seeds)
        bg_idx = border_bg
        note_seed = f"edge_bg={bg_idx} seeds={len(seeds)}"

    bg_to_trans, interior0 = ensure_transparent_index0(im, mask_bg, bg_idx)

    # recompute background mask from index 0 after swaps/remaps
    px2 = im.load()
    bg0_seeds = []
    for x in range(w):
        if px2[x,0] == 0: bg0_seeds.append((x,0))
        if px2[x,h-1] == 0: bg0_seeds.append((x,h-1))
    for y in range(h):
        if px2[0,y] == 0: bg0_seeds.append((0,y))
        if px2[w-1,y] == 0: bg0_seeds.append((w-1,y))
    mask_bg2 = floodfill_from_seeds(px2, w, h, 0, bg0_seeds)

    im2, bb, centered = center_foreground(im, mask_bg2)

    # Changed if we altered pixels OR we need to enforce tRNS(0) OR we centered.
    # (Many of your “looks like a box” cases are simply missing tRNS.)
    needs_trns = ("transparency" not in im2.info) or (im2.info.get("transparency") != 0)
    changed = (bg_to_trans > 0) or centered or needs_trns

    if apply and changed:
        im2.save(path, optimize=False, transparency=0)

    note = f"{note_seed} interior0={interior0}"
    return Result(changed, bg_to_trans, bb, note=note)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("png", nargs="+")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    for p in args.png:
        path = Path(p)
        if not path.exists():
            print(f"ERROR: missing {p}", file=sys.stderr)
            continue
        r = process(path, args.apply)
        tag = "APPLIED" if args.apply and r.changed else ("OK" if r.changed else "SKIP")
        print(f"{tag}: {p} | bg->trans px={r.bg_to_trans_pixels} | bbox={r.bbox} | {r.note}")

if __name__ == "__main__":
    main()
