#!/usr/bin/env python3
from __future__ import annotations
from PIL import Image
from pathlib import Path
import argparse
import sys

def remap_indices(img: Image.Image, mapping: dict[int,int]) -> Image.Image:
    # mapping old_index -> new_index, default identity
    px = img.load()
    w, h = img.size
    out = Image.new("P", (w, h))
    out.putpalette(img.getpalette())
    opx = out.load()
    for y in range(h):
        for x in range(w):
            v = px[x, y]
            opx[x, y] = mapping.get(v, v)
    return out

def swap_palette_entries(pal: list[int], a: int, b: int) -> list[int]:
    # pal is 768 ints (RGB triples)
    pa = pal[a*3:a*3+3]
    pb = pal[b*3:b*3+3]
    pal2 = pal[:]
    pal2[a*3:a*3+3] = pb
    pal2[b*3:b*3+3] = pa
    return pal2

def process(path: Path, apply: bool) -> tuple[bool,str]:
    im = Image.open(path)

    if im.mode != "P":
        # Convert to P but keep exact colors as much as possible.
        # (If this triggers, your pipeline has bigger issues.)
        im = im.convert("P")

    tr = im.info.get("transparency", None)
    if not isinstance(tr, int):
        return (False, "skip:no-trns")

    if tr == 0:
        return (False, "skip:trns-already-0")

    # Swap palette colors at 0 and tr, then swap pixel indices 0 <-> tr
    pal = im.getpalette()
    if pal is None:
        return (False, "skip:no-palette")

    pal2 = swap_palette_entries(pal, 0, tr)
    im2 = im.copy()
    im2.putpalette(pal2)

    # Remap indices so appearance is preserved: 0->tr and tr->0
    mapping = {0: tr, tr: 0}
    im3 = remap_indices(im2, mapping)

    # Set transparency index to 0
    im3.info["transparency"] = 0

    if apply:
        im3.save(path, optimize=False)

    return (True, f"fixed:trns {tr}->0")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("png", type=Path)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    changed, msg = process(args.png, args.apply)
    print(f"{'APPLIED' if args.apply else 'DRY'}: {args.png} :: {msg}")
    sys.exit(0)

if __name__ == "__main__":
    main()
