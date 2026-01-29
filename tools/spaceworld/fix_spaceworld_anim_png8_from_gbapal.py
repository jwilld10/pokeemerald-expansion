#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
from PIL import Image
import argparse
from collections import deque

def read_gbapal(path: Path, colors: int = 16) -> list[tuple[int,int,int]]:
    data = path.read_bytes()
    if len(data) < colors * 2:
        raise ValueError(f"{path} too small to be a gbapal ({len(data)} bytes)")
    out = []
    for i in range(colors):
        lo = data[i*2]
        hi = data[i*2 + 1]
        val = lo | (hi << 8)   # little-endian BGR555 (GBA)
        b = (val >> 10) & 0x1F
        g = (val >> 5) & 0x1F
        r = val & 0x1F
        out.append((r * 255 // 31, g * 255 // 31, b * 255 // 31))
    return out

def floodfill_background_mask(img: Image.Image, tol: int = 0) -> Image.Image:
    w, h = img.size
    rgba = img.convert("RGBA")
    pix = rgba.load()

    def close(c1, c2):
        return (abs(c1[0]-c2[0]) <= tol and abs(c1[1]-c2[1]) <= tol and abs(c1[2]-c2[2]) <= tol and abs(c1[3]-c2[3]) <= tol)

    mask = Image.new("1", (w, h), 0)
    m = mask.load()

    starts = [(0,0), (w-1,0), (0,h-1), (w-1,h-1)]
    q = deque()
    visited = set()
    for sx, sy in starts:
        q.append((sx, sy, pix[sx, sy]))

    while q:
        x, y, sc = q.popleft()
        key = (x, y, sc)
        if key in visited:
            continue
        visited.add(key)
        if x < 0 or y < 0 or x >= w or y >= h:
            continue
        if m[x,y]:
            continue
        if not close(pix[x,y], sc):
            continue
        m[x,y] = 1
        q.append((x+1,y,sc))
        q.append((x-1,y,sc))
        q.append((x,y+1,sc))
        q.append((x,y-1,sc))
    return mask

def center_on_canvas(rgba: Image.Image, canvas: int = 64) -> Image.Image:
    bbox = rgba.getbbox()
    if not bbox:
        return Image.new("RGBA", (canvas, canvas), (0,0,0,0))
    cropped = rgba.crop(bbox)
    cw, ch = cropped.size
    if cw > canvas or ch > canvas:
        raise ValueError(f"Sprite bbox {cw}x{ch} exceeds {canvas}x{canvas}. Fix source first.")
    out = Image.new("RGBA", (canvas, canvas), (0,0,0,0))
    ox = (canvas - cw) // 2
    oy = (canvas - ch) // 2
    out.paste(cropped, (ox, oy))
    return out

def make_pal_image(pal_rgb: list[tuple[int,int,int]]) -> Image.Image:
    """Create a P-mode palette image usable by quantize(palette=...)."""
    pal_img = Image.new("P", (16, 16), 0)
    flat = []
    for (r,g,b) in pal_rgb:
        flat.extend([r,g,b])
    flat += [0,0,0] * (256 - len(pal_rgb))
    pal_img.putpalette(flat)
    return pal_img

def nearest_palette_index(rgb: tuple[int,int,int], pal: list[tuple[int,int,int]], start_idx: int = 1) -> int:
    r,g,b = rgb
    best_i = start_idx
    best_d = 10**18
    for i in range(start_idx, len(pal)):
        pr,pg,pb = pal[i]
        d = (r-pr)*(r-pr) + (g-pg)*(g-pg) + (b-pb)*(b-pb)
        if d < best_d:
            best_d = d
            best_i = i
    return best_i

def convert_rgba_to_png8_with_gbapal(img_rgba: Image.Image, pal_rgb: list[tuple[int,int,int]]) -> Image.Image:
    """
    Palette-locked conversion:
    - quantize RGB against provided palette (no dithering)
    - force transparent pixels to index 0
    - prevent opaque pixels from ending up at index 0 (reassign to 1..15)
    """
    rgba = img_rgba.convert("RGBA")
    w,h = rgba.size
    r,g,b,a = rgba.split()

    # quantize requires RGB/L, not RGBA
    rgb = Image.merge("RGB", (r,g,b))

    pal_img = make_pal_image(pal_rgb)

    q = rgb.quantize(palette=pal_img, dither=Image.Dither.NONE)

    q.info["transparency"] = 0

    qp = q.load()
    ap = a.load()

    # First: force true transparent pixels to index 0
    for y in range(h):
        for x in range(w):
            if ap[x,y] == 0:
                qp[x,y] = 0

    # Second: ensure opaque pixels are NOT index 0 (keep index 0 for transparency)
    # If quantize mapped an opaque pixel to 0, remap it to nearest 1..15 by original RGB
    rgbp = rgb.load()
    for y in range(h):
        for x in range(w):
            if ap[x,y] != 0 and qp[x,y] == 0:
                qp[x,y] = nearest_palette_index(rgbp[x,y], pal_rgb, start_idx=1)

    return q

def process_png(png_path: Path, gbapal_path: Path, canvas: int = 64, tol: int = 0, apply: bool = False) -> None:
    img = Image.open(png_path).convert("RGBA")

    # background -> transparency
    bgmask = floodfill_background_mask(img, tol=tol).convert("L")
    r,g,b,a = img.split()
    a = Image.composite(Image.new("L", img.size, 0), a, bgmask)
    img = Image.merge("RGBA", (r,g,b,a))

    # center
    img = center_on_canvas(img, canvas=canvas)

    # palette-locked png8
    pal = read_gbapal(gbapal_path, colors=16)
    out = convert_rgba_to_png8_with_gbapal(img, pal)

    if apply:
        out.save(png_path, optimize=False)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="graphics/spaceworld/pokemon")
    ap.add_argument("--glob", default="**/anim_front*.png", help="Glob under root")
    ap.add_argument("--palette", default="normal.gbapal", help="Palette filename per mon (normal.gbapal or shiny.gbapal)")
    ap.add_argument("--canvas", type=int, default=64)
    ap.add_argument("--tol", type=int, default=0, help="Flood-fill tolerance (0 exact)")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    root = Path(args.root)
    paths = sorted(root.glob(args.glob))
    if not paths:
        raise SystemExit(f"No files matched: {root}/{args.glob}")

    done = 0
    for p in paths:
        pal_path = p.parent / args.palette
        if not pal_path.exists():
            print(f"SKIP (no {args.palette}): {p}")
            continue
        process_png(p, pal_path, canvas=args.canvas, tol=args.tol, apply=args.apply)
        done += 1
        print(("APPLY" if args.apply else "CHECK") + f": {p}")

    print(f"Done. Processed {done} PNG(s).")

if __name__ == "__main__":
    main()
