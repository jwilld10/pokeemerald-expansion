#!/usr/bin/env python3
import argparse
from pathlib import Path
from collections import Counter
from PIL import Image

def die(msg: str):
    raise SystemExit(msg)

def load_indexed(path: Path) -> Image.Image:
    im = Image.open(path)
    if im.mode != "P":
        die(f"ERROR: {path} is mode {im.mode}, expected indexed PNG (mode P).")
    if im.size != (64, 64):
        die(f"ERROR: {path} is {im.size}, expected 64x64.")
    pal = im.getpalette()
    if not pal or len(pal) < 768:
        die(f"ERROR: {path} has no/invalid palette.")
    return im

def get_trans_idx(im: Image.Image) -> int:
    t = im.info.get("transparency", 0)
    return t if isinstance(t, int) else 0

def find_bg_idx_by_edge_majority(im: Image.Image, trans_idx: int) -> int | None:
    w, h = im.size
    px = im.load()
    edge = []
    for x in range(w):
        edge.append(px[x, 0])
        edge.append(px[x, h-1])
    for y in range(h):
        edge.append(px[0, y])
        edge.append(px[w-1, y])

    c = Counter(edge)
    if trans_idx in c:
        del c[trans_idx]
    if not c:
        return None
    # Most common non-transparent edge index is almost always the background box
    return c.most_common(1)[0][0]

def swap_indices_and_palette(im: Image.Image, a: int, b: int):
    # swap pixel indices
    px = im.load()
    for y in range(64):
        for x in range(64):
            v = px[x, y]
            if v == a:
                px[x, y] = b
            elif v == b:
                px[x, y] = a

    # swap palette entries (RGB triples)
    pal = im.getpalette()
    a3, b3 = 3*a, 3*b
    pal[a3:a3+3], pal[b3:b3+3] = pal[b3:b3+3], pal[a3:a3+3]
    im.putpalette(pal)

def bbox_nonzero(im: Image.Image, trans_idx: int):
    px = im.load()
    minx, miny = 64, 64
    maxx, maxy = -1, -1
    for y in range(64):
        for x in range(64):
            if px[x, y] != trans_idx:
                if x < minx: minx = x
                if y < miny: miny = y
                if x > maxx: maxx = x
                if y > maxy: maxy = y
    if maxx < 0:
        return None
    return (minx, miny, maxx+1, maxy+1)

def center_to_fresh_64(im: Image.Image, trans_idx: int) -> Image.Image:
    pal = im.getpalette()
    out = Image.new("P", (64, 64), color=trans_idx)
    out.putpalette(pal)
    out.info["transparency"] = trans_idx

    bb = bbox_nonzero(im, trans_idx)
    if bb is None:
        return out

    crop = im.crop(bb)
    cw, ch = crop.size
    ox = (64 - cw) // 2
    oy = (64 - ch) // 2
    out.paste(crop, (ox, oy))
    return out

def process(path: Path, apply: bool):
    im = load_indexed(path)
    # We enforce index 0 as transparent for Emerald/gbagfx sanity
    trans_idx = 0

    # Detect the “box/background” index from edges (most common edge color)
    bg_idx = find_bg_idx_by_edge_majority(im, trans_idx)
    if bg_idx is None:
        # Nothing to do except centering + set transparency
        out = center_to_fresh_64(im, trans_idx)
        if apply:
            out.info["transparency"] = trans_idx
            out.save(path, format="PNG", optimize=False)
        bb = bbox_nonzero(out, trans_idx)
        print(f"{'APPLIED' if apply else 'DRYRUN'}: {path} | bg_idx=None | bbox={bb}")
        return

    # If the background isn’t already index 0, swap it with 0.
    # This simultaneously:
    #   - makes the background pixels become index 0 (transparent)
    #   - moves whatever was index 0 (the “missing white”) away from transparency
    if bg_idx != 0:
        swap_indices_and_palette(im, 0, bg_idx)

    # Force tRNS index 0
    im.info["transparency"] = 0

    # Center on a fresh canvas (does not recolor/requantize)
    out = center_to_fresh_64(im, 0)

    if apply:
        out.info["transparency"] = 0
        out.save(path, format="PNG", optimize=False)

    bb = bbox_nonzero(out, 0)
    print(f"{'APPLIED' if apply else 'DRYRUN'}: {path} | swapped_bg_idx={bg_idx} -> 0 | bbox={bb}")

def main():
    ap = argparse.ArgumentParser(
        description="Fix Spaceworld summary pics: remove box WITHOUT touching sprite colors by swapping edge-bg index with index0 (transparent), then center on fresh 64x64."
    )
    ap.add_argument("paths", nargs="+", help="64x64 indexed PNG(s) (mode P).")
    ap.add_argument("--apply", action="store_true", help="Write changes in-place.")
    args = ap.parse_args()

    ok = True
    for p in args.paths:
        try:
            process(Path(p), args.apply)
        except Exception as e:
            ok = False
            print(f"ERROR: {p}: {e}")
    raise SystemExit(0 if ok else 2)

if __name__ == "__main__":
    main()
