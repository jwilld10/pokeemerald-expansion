#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
from collections import deque, Counter
import argparse
import sys
from PIL import Image

# Heuristics tuned for 64x64 summary pics with a "stripe" BG in the PNG.
MIN_BOX_REGION = 200   # connected pixels of one color needed to consider it a "bad box"
EDGE_SAMPLE = 2        # how many pixels inward to sample for "likely background"

def loadP(path: Path) -> Image.Image:
    im = Image.open(path)
    if im.mode != "P" or im.size != (64, 64):
        raise ValueError(f"{path}: expected P 64x64, got {im.mode} {im.size}")
    return im

def get_edge_bg_colors(im: Image.Image) -> set[int]:
    px = im.load()
    w, h = im.size
    colors = Counter()
    # sample a 2px border ring, not just outermost pixel
    for y in range(EDGE_SAMPLE):
        for x in range(w):
            colors[px[x, y]] += 1
            colors[px[x, h-1-y]] += 1
    for x in range(EDGE_SAMPLE):
        for y in range(h):
            colors[px[x, y]] += 1
            colors[px[w-1-x, y]] += 1
    # take the top few as "background-like"
    return {c for c, _ in colors.most_common(6)}

def connected_regions_of_color(px, color: int):
    w = 64; h = 64
    seen = [[False]*w for _ in range(h)]
    regions = []
    for y in range(h):
        for x in range(w):
            if seen[y][x] or px[x,y] != color:
                continue
            q = deque([(x,y)])
            seen[y][x] = True
            cells = []
            while q:
                cx, cy = q.popleft()
                cells.append((cx,cy))
                for nx, ny in ((cx+1,cy),(cx-1,cy),(cx,cy+1),(cx,cy-1)):
                    if 0 <= nx < w and 0 <= ny < h and not seen[ny][nx] and px[nx,ny] == color:
                        seen[ny][nx] = True
                        q.append((nx,ny))
            regions.append(cells)
    return regions

def compute_sprite_mask_by_ref(cur_px, ref_px, ref_bg_colors: set[int]):
    # sprite pixels are those where current differs from reference background pattern
    # but boxes also differ, so we'll remove box colors first using connectivity.
    w=h=64
    mask = [[False]*w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            # if reference pixel is background-ish and current pixel differs, that could be sprite or box
            if ref_px[x,y] in ref_bg_colors and cur_px[x,y] != ref_px[x,y]:
                mask[y][x] = True
    return mask

def bbox_from_mask(mask):
    xs=[]; ys=[]
    for y in range(64):
        for x in range(64):
            if mask[y][x]:
                xs.append(x); ys.append(y)
    if not xs:
        return None
    return (min(xs), min(ys), max(xs)+1, max(ys)+1)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref-root", required=True, help="Reference root directory (mirrors graphics/spaceworld/pokemon structure)")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("pngs", nargs="+")
    args = ap.parse_args()

    ref_root = Path(args.ref_root)

    changed = 0
    for p in args.pngs:
        cur_path = Path(p)
        if not cur_path.exists():
            print(f"ERROR: missing {cur_path}", file=sys.stderr)
            continue

        # map to reference path by replacing leading graphics/spaceworld/pokemon with ref_root
        parts = cur_path.parts
        try:
            idx = parts.index("spaceworld")
        except ValueError:
            print(f"SKIP: {cur_path} (not under graphics/spaceworld/...)", file=sys.stderr)
            continue

        # expected: .../graphics/spaceworld/pokemon/<name>/<file>.png
        # build relative from "pokemon/..."
        try:
            pidx = parts.index("pokemon")
        except ValueError:
            print(f"SKIP: {cur_path} (no /pokemon/ in path)", file=sys.stderr)
            continue

        rel = Path(*parts[pidx:])  # pokemon/<name>/anim_front*.png
        ref_path = ref_root / rel

        if not ref_path.exists():
            # Fallback: search within ref_root for the same pokemon folder + filename
            # (covers cases where ref_root layout differs slightly)
            species_dir = rel.parts[1] if len(rel.parts) >= 2 else None  # pokemon/<species>/file
            if species_dir:
                candidates = list(ref_root.rglob(f"{species_dir}/{cur_path.name}"))
                if candidates:
                    ref_path = candidates[0]
            if not ref_path.exists():
                print(f"SKIP: {cur_path} (no ref: {ref_root / rel})")
                continue

        try:
            cur = loadP(cur_path)
            ref = loadP(ref_path)
        except Exception as e:
            print(f"ERROR: {cur_path}: {e}")
            continue

        # Ensure output keeps reference palette to preserve exact bg + colors
        out = ref.copy()
        out.putpalette(ref.getpalette())

        cur_px = cur.load()
        ref_px = ref.load()
        out_px = out.load()

        ref_bg_colors = get_edge_bg_colors(ref)

        # 1) Find dominant "box colors" by looking at pixels where ref is bg but cur differs
        diff_colors = Counter()
        for y in range(64):
            for x in range(64):
                if ref_px[x,y] in ref_bg_colors and cur_px[x,y] != ref_px[x,y]:
                    diff_colors[cur_px[x,y]] += 1

        # pick top candidates (often black/pink/purple)
        candidates = [c for c, n in diff_colors.most_common(4)]

        # 2) Remove large connected regions of those candidate colors (replace with reference BG)
        removed = 0
        for c in candidates:
            regions = connected_regions_of_color(cur_px, c)
            for cells in regions:
                if len(cells) >= MIN_BOX_REGION:
                    for (x,y) in cells:
                        # replace ONLY where reference is background-ish to avoid sprite damage
                        if ref_px[x,y] in ref_bg_colors:
                            # set current to reference at that pixel by writing into out later
                            pass
                    # We'll just rely on reference background in `out` (already there)
                    removed += len(cells)

        # 3) Now compute sprite mask as "pixels where ref is bg and cur differs AND not in box regions"
        # Build a fast lookup of box pixels: any candidate color pixel connected-region >= threshold
        box_pix = [[False]*64 for _ in range(64)]
        for c in candidates:
            regions = connected_regions_of_color(cur_px, c)
            for cells in regions:
                if len(cells) >= MIN_BOX_REGION:
                    for (x,y) in cells:
                        if ref_px[x,y] in ref_bg_colors:
                            box_pix[y][x] = True

        sprite_mask = [[False]*64 for _ in range(64)]
        for y in range(64):
            for x in range(64):
                if ref_px[x,y] in ref_bg_colors and cur_px[x,y] != ref_px[x,y] and not box_pix[y][x]:
                    sprite_mask[y][x] = True
                # also include pixels where ref is NOT bg (sprite area in ref), because current sprite may overlap there
                if ref_px[x,y] not in ref_bg_colors and cur_px[x,y] != ref_px[x,y]:
                    sprite_mask[y][x] = True

        bb = bbox_from_mask(sprite_mask)

        if bb is None:
            print(f"OK: {cur_path} | no sprite mask found; left as reference")
            continue

        x0,y0,x1,y1 = bb
        sw, sh = (x1-x0), (y1-y0)
        ox = (64 - sw)//2
        oy = (64 - sh)//2

        # 4) Blit sprite pixels from current onto reference background, centered.
        # Only copy pixels that are part of the sprite mask.
        for y in range(y0, y1):
            for x in range(x0, x1):
                if sprite_mask[y][x]:
                    nx = ox + (x - x0)
                    ny = oy + (y - y0)
                    out_px[nx, ny] = cur_px[x, y]

        # 5) Decide if changed (box removed and/or different placement)
        # We consider changed if bbox isn't already centered-ish or if box pixels exist
        has_box = any(any(row) for row in box_pix)
        already_centered = (ox == x0 and oy == y0)  # rough; good enough for deciding "changed"
        did_change = has_box or (not already_centered)

        if args.apply and did_change:
            out.save(cur_path, optimize=False)
            changed += 1
            print(f"APPLIED: {cur_path} | boxCandidates={candidates} removed~={removed} | bbox={bb} -> offset=({ox},{oy})")
        else:
            print(f"OK: {cur_path} | boxCandidates={candidates} removed~={removed} | bbox={bb} -> offset=({ox},{oy})")

    print(f"Done. Changed {changed} file(s).")

if __name__ == "__main__":
    main()
