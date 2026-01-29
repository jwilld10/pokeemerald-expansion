#!/usr/bin/env python3
from pathlib import Path
from PIL import Image
import argparse

def read_gbapal(path: Path, colors=16):
    data = path.read_bytes()
    out = []
    for i in range(colors):
        lo = data[i*2]
        hi = data[i*2+1]
        v = lo | (hi<<8)      # BGR555
        b = (v>>10)&31
        g = (v>>5)&31
        r = v&31
        out.append((r*255//31, g*255//31, b*255//31))
    return out

def make_pal_img(pal_rgb):
    pal_img = Image.new("P", (16,16), 0)
    flat = []
    for (r,g,b) in pal_rgb:
        flat += [r,g,b]
    flat += [0,0,0] * (256 - len(pal_rgb))
    pal_img.putpalette(flat)
    return pal_img

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("png", type=Path)
    ap.add_argument("gbapal", type=Path)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    im = Image.open(args.png).convert("RGBA")
    pal_rgb = read_gbapal(args.gbapal, 16)

    # Preserve transparency exactly from alpha: alpha==0 -> transparent
    r,g,b,a = im.split()
    rgb = Image.merge("RGB", (r,g,b))

    # Quantize RGB to the exact palette order from gbapal
    pal_img = make_pal_img(pal_rgb)
    q = rgb.quantize(palette=pal_img, dither=Image.Dither.NONE)

    # Force transparency to index 0 wherever alpha==0
    q.info["transparency"] = 0
    qp = q.load()
    apx = a.load()
    w,h = q.size
    for y in range(h):
        for x in range(w):
            if apx[x,y] == 0:
                qp[x,y] = 0

    if args.apply:
        q.save(args.png, optimize=False)
        print("APPLIED:", args.png)
    else:
        print("CHECK OK:", args.png)

if __name__ == "__main__":
    main()
