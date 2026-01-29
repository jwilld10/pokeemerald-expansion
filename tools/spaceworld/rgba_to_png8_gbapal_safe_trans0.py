#!/usr/bin/env python3
from PIL import Image
from collections import deque, Counter
from pathlib import Path
import argparse, math, sys

def read_gbapal(path: Path):
    data = path.read_bytes()
    if len(data) < 32:
        raise ValueError(f"{path}: too small to be 16-color .gbapal (need 32 bytes)")
    cols = []
    for i in range(16):
        v = data[i*2] | (data[i*2+1] << 8)
        # GBA: bits 0-4=R, 5-9=G, 10-14=B
        r5 = (v & 0x1F)
        g5 = (v >> 5) & 0x1F
        b5 = (v >> 10) & 0x1F
        cols.append((r5 * 255 // 31, g5 * 255 // 31, b5 * 255 // 31))
    return cols

def nearest_index(rgb, pal):
    r,g,b = rgb
    best_i = 0
    best_d = 10**18
    for i,(pr,pg,pb) in enumerate(pal):
        dr = r - pr
        dg = g - pg
        db = b - pb
        d = dr*dr + dg*dg + db*db
        if d < best_d:
            best_d = d
            best_i = i
    return best_i

def paste_center_to_64(im_rgba: Image.Image):
    w,h = im_rgba.size
    if (w,h) == (64,64):
        return im_rgba
    out = Image.new("RGBA", (64,64), (0,0,0,0))
    ox = (64 - w)//2
    oy = (64 - h)//2
    out.paste(im_rgba, (ox, oy))
    return out

def floodfill_edge_bg_to_trans(im_rgba: Image.Image, tol=0):
    w,h = im_rgba.size
    px = im_rgba.load()

    # pick bg as most common of 4 corners
    corners = [px[0,0], px[w-1,0], px[0,h-1], px[w-1,h-1]]
    bg = Counter(corners).most_common(1)[0][0]

    def close(c):
        return (abs(c[0]-bg[0])<=tol and abs(c[1]-bg[1])<=tol and abs(c[2]-bg[2])<=tol and abs(c[3]-bg[3])<=tol)

    q = deque()
    seen = set()
    for x in range(w):
        q.append((x,0)); q.append((x,h-1))
    for y in range(h):
        q.append((0,y)); q.append((w-1,y))

    removed = 0
    while q:
        x,y = q.popleft()
        if (x,y) in seen:
            continue
        seen.add((x,y))
        c = px[x,y]
        if close(c):
            px[x,y] = (0,0,0,0)
            removed += 1
            if x>0: q.append((x-1,y))
            if x<w-1: q.append((x+1,y))
            if y>0: q.append((x,y-1))
            if y<h-1: q.append((x,y+1))

    # harden alpha (gbagfx hates partial alpha)
    for y in range(h):
        for x in range(w):
            r,g,b,a = px[x,y]
            px[x,y] = (r,g,b, 0 if a==0 else 255)

    return removed

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("png", type=Path)
    ap.add_argument("gbapal", type=Path)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--tol", type=int, default=0)
    args = ap.parse_args()

    pal = read_gbapal(args.gbapal)

    src = Image.open(args.png).convert("RGBA")
    src = paste_center_to_64(src)
    removed = floodfill_edge_bg_to_trans(src, tol=args.tol)

    w,h = src.size
    spx = src.load()

    # First pass: map all opaque pixels to palette indices
    idx_img = Image.new("P", (w,h))
    idx = idx_img.load()

    used_by_opaque = Counter()
    for y in range(h):
        for x in range(w):
            r,g,b,a = spx[x,y]
            if a == 0:
                idx[x,y] = 0  # placeholder for now
            else:
                ii = nearest_index((r,g,b), pal)
                idx[x,y] = ii
                used_by_opaque[ii] += 1

    # Choose a transparency index that is NOT used by opaque pixels
    free = [i for i in range(16) if used_by_opaque[i] == 0]
    if not free:
        raise SystemExit(f"ERROR: {args.png}: all 16 palette entries are used by opaque pixels; cannot reserve a safe transparent index.")
    trans_i = free[0]  # any free slot works

    # Write transparent pixels as that reserved index
    for y in range(h):
        for x in range(w):
            if spx[x,y][3] == 0:
                idx[x,y] = trans_i

    # Ensure transparency is at index 0 (gbagfx expectation)
    if trans_i != 0:
        # swap palette entries 0 and trans_i, and swap indices 0 and trans_i in the image
        for y in range(h):
            for x in range(w):
                v = idx[x,y]
                if v == 0:
                    idx[x,y] = trans_i
                elif v == trans_i:
                    idx[x,y] = 0
        pal2 = pal[:]
        pal2[0], pal2[trans_i] = pal2[trans_i], pal2[0]
        pal = pal2

    flatpal = []
    for (r,g,b) in pal:
        flatpal += [r,g,b]
    idx_img.putpalette(flatpal + [0]*(768-len(flatpal)))
    idx_img.info["transparency"] = 0

    if args.apply:
        idx_img.save(args.png)
        print(f"APPLIED: {args.png} | centered=64x64 | edge_bg_removed={removed} | trans_index0_reserved=YES")
    else:
        print(f"CHECK:  {args.png} | centered=64x64 | edge_bg_removed={removed} | would_write_png8_trans0")

if __name__ == "__main__":
    main()
