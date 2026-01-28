#!/usr/bin/env python3
from __future__ import annotations
import argparse
import struct
from pathlib import Path
from PIL import Image

W, H = 32, 64
FRAME_H = 32

def bgr555_to_rgb(c: int):
    r = (c & 0x1F) << 3
    g = ((c >> 5) & 0x1F) << 3
    b = ((c >> 10) & 0x1F) << 3
    return (r, g, b)

def read_gbapal(path: Path):
    data = path.read_bytes()
    cols = struct.unpack("<16H", data[:32])
    return [bgr555_to_rgb(c) for c in cols]

def read_4bpp_icon(path: Path):
    data = path.read_bytes()
    if len(data) != 1024:
        raise ValueError(f"{path}: expected 1024 bytes, got {len(data)}")

    pixels = [[0]*32 for _ in range(64)]
    off = 0
    for ty in range(8):
        for tx in range(4):
            tile = data[off:off+32]
            off += 32
            for row in range(8):
                y = ty*8 + row
                xb = tile[row*4:(row+1)*4]
                x = tx*8
                i = 0
                for b in xb:
                    pixels[y][x+i]   = b & 0xF
                    pixels[y][x+i+1] = (b >> 4) & 0xF
                    i += 2
    return pixels

def to_image(pix, pal):
    img = Image.new("RGBA", (32, 32))
    for y in range(32):
        for x in range(32):
            v = pix[y][x]
            if v == 0:
                img.putpixel((x,y), (0,0,0,0))
            else:
                r,g,b = pal[v]
                img.putpixel((x,y), (r,g,b,255))
    return img

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--icons", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--gbapal", required=True)
    args = ap.parse_args()

    pal = read_gbapal(Path(args.gbapal))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    for p in sorted(Path(args.icons).glob("*.4bpp")):
        pix = read_4bpp_icon(p)
        f0 = pix[:32]
        f1 = pix[32:]
        to_image(f0, pal).save(out / f"{p.stem}_f0.png")
        to_image(f1, pal).save(out / f"{p.stem}_f1.png")

    print("Previews written to", out)

if __name__ == "__main__":
    main()
