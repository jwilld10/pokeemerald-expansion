#!/usr/bin/env python3
from PIL import Image
from pathlib import Path
import argparse
import math

def read_gbapal_16(path: Path):
    data = path.read_bytes()
    if len(data) < 32:
        raise SystemExit(f"ERROR: {path}: expected >=32 bytes, got {len(data)}")

    cols = []
    for i in range(0, 32, 2):
        v = data[i] | (data[i+1] << 8)  # little endian
        # GBA is BGR555 stored as: bits 0-4=R, 5-9=G, 10-14=B
        r5 = (v & 0x1F)
        g5 = (v >> 5) & 0x1F
        b5 = (v >> 10) & 0x1F
        # expand to 8-bit for matching
        cols.append((r5 * 255 // 31, g5 * 255 // 31, b5 * 255 // 31))
    return cols  # len 16

def nearest_palette_index(rgb, pal, start_idx=1):
    # Return nearest palette index among pal[start_idx..15]
    r,g,b = rgb
    best_i = start_idx
    best_d = 10**18
    for i in range(start_idx, 16):
        pr,pg,pb = pal[i]
        dr = r - pr
        dg = g - pg
        db = b - pb
        d = dr*dr + dg*dg + db*db
        if d < best_d:
            best_d = d
            best_i = i
    return best_i

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("png", type=Path)
    ap.add_argument("gbapal", type=Path)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--no-pad", action="store_true", help="Do not center-pad to 64x64")
    args = ap.parse_args()

    pal = read_gbapal_16(args.gbapal)

    src = Image.open(args.png).convert("RGBA")
    sw, sh = src.size

    # Force binary alpha (0 or 255)
    spx = src.load()
    for y in range(sh):
        for x in range(sw):
            r,g,b,a = spx[x,y]
            spx[x,y] = (r,g,b, 0 if a == 0 else 255)

    if not args.no_pad and (sw, sh) != (64, 64):
        dst = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        ox = (64 - sw) // 2
        oy = (64 - sh) // 2
        dst.alpha_composite(src, (ox, oy))
    else:
        dst = src

    w, h = dst.size
    dpx = dst.load()

    # Build indexed image
    out = Image.new("P", (w, h))
    opx = out.load()

    # Write PNG palette (RGB triples). Note: index 0 RGB can be anything; we keep gbapal[0].
    flatpal = []
    for i in range(16):
        flatpal.extend(pal[i])
    # pad to 256 entries (P mode needs 768 bytes palette)
    flatpal.extend([0,0,0] * (256 - 16))
    out.putpalette(flatpal)

    # Map pixels:
    #  - alpha 0 -> index 0
    #  - alpha 255 -> nearest among indices 1..15 (NEVER 0)
    changed = 0
    for y in range(h):
        for x in range(w):
            r,g,b,a = dpx[x,y]
            if a == 0:
                opx[x,y] = 0
            else:
                idx = nearest_palette_index((r,g,b), pal, start_idx=1)
                opx[x,y] = idx

    # Set transparency chunk (tRNS) to index 0
    out.info["transparency"] = 0

    if args.apply:
        out.save(args.png)
        print(f"APPLIED: {args.png} | mode=P size={w}x{h} transparency_index=0")
    else:
        print(f"CHECK:  {args.png} | would write mode=P size={w}x{h} transparency_index=0")

if __name__ == "__main__":
    main()
