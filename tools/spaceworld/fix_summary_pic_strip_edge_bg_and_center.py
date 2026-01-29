#!/usr/bin/env python3
from PIL import Image
from collections import deque
from pathlib import Path
import sys

def edge_flood_to_trans0(img: Image.Image) -> int:
    """
    Turn any pixels connected to the image border into palette index 0,
    but ONLY along regions of the same palette index (exact match).
    Returns count of pixels changed.
    """
    if img.mode != "P":
        raise SystemExit("ERROR: image must be palette (mode P)")

    w, h = img.size
    pix = img.load()
    visited = [[False]*w for _ in range(h)]
    q = deque()

    def push(x, y):
        if 0 <= x < w and 0 <= y < h and not visited[y][x]:
            visited[y][x] = True
            q.append((x, y))

    # Seed queue with ALL border pixels (except already-transparent ones)
    for x in range(w):
        if pix[x, 0] != 0: push(x, 0)
        if pix[x, h-1] != 0: push(x, h-1)
    for y in range(h):
        if pix[0, y] != 0: push(0, y)
        if pix[w-1, y] != 0: push(w-1, y)

    changed = 0
    while q:
        x, y = q.popleft()
        idx = pix[x, y]
        if idx == 0:
            continue

        # Flood-fill ONLY the same index region
        # Turn it to 0 and expand to 4-neighbors with same idx.
        pix[x, y] = 0
        changed += 1

        for nx, ny in ((x-1,y), (x+1,y), (x,y-1), (x,y+1)):
            if 0 <= nx < w and 0 <= ny < h and not visited[ny][nx]:
                if pix[nx, ny] == idx:
                    visited[ny][nx] = True
                    q.append((nx, ny))

    return changed

def bbox_nonzero(img: Image.Image):
    w, h = img.size
    pix = img.load()
    xs, ys = [], []
    for y in range(h):
        for x in range(w):
            if pix[x, y] != 0:
                xs.append(x); ys.append(y)
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)

def center_sprite_keep_palette(img: Image.Image) -> Image.Image:
    bb = bbox_nonzero(img)
    if bb is None:
        return img
    minx, miny, maxx, maxy = bb
    bw = maxx - minx + 1
    bh = maxy - miny + 1

    out = Image.new("P", (64, 64), 0)
    out.putpalette(img.getpalette())

    ox = (64 - bw) // 2
    oy = (64 - bh) // 2
    src = img.crop((minx, miny, maxx+1, maxy+1))
    out.paste(src, (ox, oy))
    return out

def main(png_path: str):
    p = Path(png_path)
    img = Image.open(p)

    if img.mode != "P":
        raise SystemExit(f"ERROR: {p} is not palette (P) mode (got {img.mode})")
    if img.size != (64, 64):
        raise SystemExit(f"ERROR: {p} is not 64x64 (got {img.size})")

    changed = edge_flood_to_trans0(img)
    out = center_sprite_keep_palette(img)
    out.save(p)

    bb = bbox_nonzero(out)
    print(f"APPLIED: {p} | edge->trans0 pixels={changed} | bbox={bb}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: fix_summary_pic_strip_edge_bg_and_center.py <anim_front.png>")
        sys.exit(1)
    main(sys.argv[1])
