#!/usr/bin/env python3
from __future__ import annotations
import argparse
from collections import deque
from pathlib import Path
from PIL import Image

def load_paletted(p: Path) -> Image.Image:
    im = Image.open(p)
    if im.mode != "P":
        raise SystemExit(f"ERROR: {p}: expected paletted PNG (mode P), got {im.mode}")
    if im.size != (64, 64):
        raise SystemExit(f"ERROR: {p}: expected 64x64, got {im.size}")
    return im

def border_bg_index(im: Image.Image) -> int:
    w, h = im.size
    px = im.load()
    counts = {}
    # count indices along border
    for x in range(w):
        counts[px[x, 0]] = counts.get(px[x, 0], 0) + 1
        counts[px[x, h - 1]] = counts.get(px[x, h - 1], 0) + 1
    for y in range(h):
        counts[px[0, y]] = counts.get(px[0, y], 0) + 1
        counts[px[w - 1, y]] = counts.get(px[w - 1, y], 0) + 1
    # choose most common border index
    return max(counts.items(), key=lambda kv: kv[1])[0]

def floodfill_border_mask(im: Image.Image, bg_idx: int) -> set[tuple[int,int]]:
    w, h = im.size
    px = im.load()
    q = deque()
    seen = set()
    # seed from all border pixels matching bg_idx
    for x in range(w):
        if px[x, 0] == bg_idx: q.append((x, 0))
        if px[x, h-1] == bg_idx: q.append((x, h-1))
    for y in range(h):
        if px[0, y] == bg_idx: q.append((0, y))
        if px[w-1, y] == bg_idx: q.append((w-1, y))

    while q:
        x, y = q.popleft()
        if (x, y) in seen: continue
        if px[x, y] != bg_idx: continue
        seen.add((x, y))
        if x > 0: q.append((x-1, y))
        if x < w-1: q.append((x+1, y))
        if y > 0: q.append((x, y-1))
        if y < h-1: q.append((x, y+1))
    return seen

def find_unused_index(im: Image.Image) -> int | None:
    used = set(im.getdata())
    # Prefer an actually-unused index so we don't change any existing pixels except bg
    for i in range(256):
        if i not in used:
            return i
    return None

def swap_palette_entries(pal: list[int], a: int, b: int) -> None:
    # pal is [r,g,b,r,g,b,...]
    ai, bi = 3*a, 3*b
    pal[ai:ai+3], pal[bi:bi+3] = pal[bi:bi+3], pal[ai:ai+3]

def remap_index(im: Image.Image, src: int, dst: int) -> int:
    data = list(im.getdata())
    changed = 0
    for i,v in enumerate(data):
        if v == src:
            data[i] = dst
            changed += 1
    im.putdata(data)
    return changed

def main():
    ap = argparse.ArgumentParser(description="Make border-connected BG transparent using a dedicated palette index (no color changes).")
    ap.add_argument("png_path")
    ap.add_argument("--apply", action="store_true", help="Write changes to the PNG. Without this, dry-run.")
    ap.add_argument("--to-index0", action="store_true", help="Move the chosen transparency index to palette index 0 (and remap pixels) without color changes.")
    args = ap.parse_args()

    p = Path(args.png_path)
    im = load_paletted(p)

    bg = border_bg_index(im)
    mask = floodfill_border_mask(im, bg)

    if not mask:
        print(f"APPLIED: {p} | no border BG detected | changed=0 | trans=None")
        return

    # choose dedicated transparency index
    unused = find_unused_index(im)
    if unused is None:
        # extremely rare for 64x64 png8 (would require all 256 indices used)
        raise SystemExit(f"ERROR: {p}: all 256 palette indices are used; can't allocate dedicated BG index safely.")

    # Remap ONLY the border-connected background pixels to the unused index
    data = list(im.getdata())
    w,h = im.size
    changed = 0
    for (x,y) in mask:
        idx = y*w + x
        if data[idx] != unused:
            data[idx] = unused
            changed += 1
    im.putdata(data)

    trans_idx = unused

    # Optionally move transparency to index 0 (swap palette entries + remap indices)
    if args.to_index0 and trans_idx != 0:
        pal = im.getpalette()
        # Swap palette colors between trans_idx and 0
        swap_palette_entries(pal, 0, trans_idx)
        im.putpalette(pal)
        # Remap pixels: indices 0 <-> trans_idx
        data = list(im.getdata())
        swapped = 0
        for i,v in enumerate(data):
            if v == 0:
                data[i] = trans_idx
                swapped += 1
            elif v == trans_idx:
                data[i] = 0
                swapped += 1
        im.putdata(data)
        trans_idx = 0

    if args.apply:
        # Save with explicit transparency index -> writes tRNS chunk
        im.save(p, format="PNG", transparency=trans_idx)
        print(f"APPLIED: {p} | bg(border idx)={bg} -> trans_idx={trans_idx} | bg_pixels={changed}")
    else:
        print(f"DRY: {p} | bg(border idx)={bg} -> trans_idx={trans_idx} | bg_pixels={changed}")

if __name__ == "__main__":
    main()
