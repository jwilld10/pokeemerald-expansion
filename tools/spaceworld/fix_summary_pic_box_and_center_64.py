#!/usr/bin/env python3
import argparse
from collections import deque
from pathlib import Path
from PIL import Image

def load_indexed(path: Path) -> Image.Image:
    im = Image.open(path)
    if im.mode != "P":
        raise SystemExit(f"ERROR: {path} is mode {im.mode}, expected indexed PNG (mode P).")
    return im

def get_transparent_index(im: Image.Image) -> int:
    t = im.info.get("transparency", None)
    return t if isinstance(t, int) else 0

def edge_indices(im: Image.Image, trans_idx: int):
    w, h = im.size
    px = im.load()
    s = set()
    for x in range(w):
        s.add(px[x, 0])
        s.add(px[x, h - 1])
    for y in range(h):
        s.add(px[0, y])
        s.add(px[w - 1, y])
    s.discard(trans_idx)
    return sorted(s)

def flood_component_from_edges(im: Image.Image, target_idx: int):
    """Return list of (x,y) pixels in the edge-reachable component of target_idx."""
    w, h = im.size
    px = im.load()
    q = deque()
    seen = set()
    comp = []

    def try_push(x, y):
        if (x, y) in seen:
            return
        if px[x, y] != target_idx:
            return
        seen.add((x, y))
        q.append((x, y))

    for x in range(w):
        try_push(x, 0)
        try_push(x, h - 1)
    for y in range(h):
        try_push(0, y)
        try_push(w - 1, y)

    while q:
        x, y = q.popleft()
        comp.append((x, y))
        if x > 0:     try_push(x - 1, y)
        if x < w - 1: try_push(x + 1, y)
        if y > 0:     try_push(x, y - 1)
        if y < h - 1: try_push(x, y + 1)

    return comp

def bbox_non_transparent(im: Image.Image, trans_idx: int):
    w, h = im.size
    px = im.load()
    minx, miny = w, h
    maxx, maxy = -1, -1
    for y in range(h):
        for x in range(w):
            if px[x, y] != trans_idx:
                if x < minx: minx = x
                if y < miny: miny = y
                if x > maxx: maxx = x
                if y > maxy: maxy = y
    if maxx < 0:
        return None
    return (minx, miny, maxx + 1, maxy + 1)

def center_on_fresh_canvas_64(im: Image.Image, trans_idx: int) -> Image.Image:
    pal = im.getpalette()
    if pal is None:
        raise SystemExit("ERROR: Image has no palette data.")

    bb = bbox_non_transparent(im, trans_idx)
    out = Image.new("P", (64, 64), color=trans_idx)
    out.putpalette(pal)
    out.info["transparency"] = trans_idx

    if bb is None:
        return out

    crop = im.crop(bb)
    cw, ch = crop.size
    if cw > 64 or ch > 64:
        raise SystemExit(f"ERROR: Non-transparent bbox is {cw}x{ch}, larger than 64x64.")

    ox = (64 - cw) // 2
    oy = (64 - ch) // 2
    out.paste(crop, (ox, oy))
    return out

def save_indexed_png(im: Image.Image, path: Path, trans_idx: int):
    im.info["transparency"] = trans_idx
    # keep it PNG8 indexed; no recolor/requantize
    im.save(path, format="PNG", optimize=False)

def process_one(path: Path, apply: bool, min_clear_ratio: float):
    im = load_indexed(path)
    if im.size != (64, 64):
        raise SystemExit(f"ERROR: {path} is {im.size}, expected 64x64.")

    trans_idx = get_transparent_index(im)
    px = im.load()
    total = 64 * 64
    min_clear_px = int(total * min_clear_ratio)

    cleared_total = 0
    # For each unique edge color: clear ONLY if the edge-connected component is "background-sized"
    for idx in edge_indices(im, trans_idx):
        comp = flood_component_from_edges(im, idx)
        if not comp:
            continue
        if len(comp) >= min_clear_px:
            for (x, y) in comp:
                px[x, y] = trans_idx
            cleared_total += len(comp)

    out = center_on_fresh_canvas_64(im, trans_idx)

    if apply:
        save_indexed_png(out, path, trans_idx)

    bb = bbox_non_transparent(out, trans_idx)
    bbox_str = "None" if bb is None else str((bb[0], bb[1], bb[2]-1, bb[3]-1))
    print(f"{'APPLIED' if apply else 'DRYRUN'}: {path} | cleared_px={cleared_total} | bbox={bbox_str} | min_clear_px={min_clear_px}")

def main():
    ap = argparse.ArgumentParser(
        description="Remove large edge-connected background boxes and center sprite on a fresh 64x64 canvas, preserving palette indices."
    )
    ap.add_argument("paths", nargs="+", help="PNG(s) to process (must be indexed 64x64 PNG8, mode P).")
    ap.add_argument("--apply", action="store_true", help="Write changes in-place. Otherwise dry-run.")
    ap.add_argument("--min-clear-ratio", type=float, default=0.20,
                    help="Only clear an edge-connected region if it covers at least this fraction of the image (default 0.20).")
    args = ap.parse_args()

    ok = True
    for p in args.paths:
        try:
            process_one(Path(p), apply=args.apply, min_clear_ratio=args.min_clear_ratio)
        except Exception as e:
            ok = False
            print(f"ERROR: {p}: {e}")
    raise SystemExit(0 if ok else 2)

if __name__ == "__main__":
    main()
