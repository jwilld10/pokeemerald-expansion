#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
from collections import deque
from PIL import Image

SRC = Path("graphics/spaceworld/shared_icons")
OUT = SRC / "fixed_32x64_index0_clean"
OUT.mkdir(parents=True, exist_ok=True)

TOL = 10

def close_rgb(a, b):
    return all(abs(int(a[i]) - int(b[i])) <= TOL for i in range(3))

def bg_connected_mask(im_rgba: Image.Image):
    """Mask of background-ish pixels connected to (0,0)."""
    im = im_rgba.convert("RGBA")
    w, h = im.size
    px = im.load()
    bg = px[0,0][:3]
    q = deque([(0,0)])
    seen = {(0,0)}
    mask = [[False]*w for _ in range(h)]
    while q:
        x,y = q.popleft()
        if close_rgb(px[x,y][:3], bg):
            mask[y][x] = True
            for nx, ny in ((x+1,y),(x-1,y),(x,y+1),(x,y-1)):
                if 0 <= nx < w and 0 <= ny < h and (nx,ny) not in seen:
                    seen.add((nx,ny))
                    q.append((nx,ny))
    return mask

def extract_frames(src_rgba: Image.Image):
    """
    Handles either:
      - 16x16 single-frame icons (we'll synthesize 2 frames by duplicating), OR
      - 32x64 already-stacked frames (top/bottom 32x32), OR
      - 32x32 single frame (duplicate)
    """
    w, h = src_rgba.size
    if (w, h) == (32, 64):
        f0 = src_rgba.crop((0, 0, 32, 32))
        f1 = src_rgba.crop((0, 32, 32, 64))
        return f0, f1
    if (w, h) == (32, 32):
        return src_rgba, src_rgba
    if (w, h) == (16, 16):
        return src_rgba, src_rgba
    # fallback: just center-crop into 32x32 then duplicate
    f0 = Image.new("RGBA", (32,32), (0,0,0,0))
    tmp = src_rgba.copy()
    tmp = tmp.crop((0,0,min(w,32),min(h,32)))
    f0.paste(tmp, (0,0))
    return f0, f0

def paste_foreground(dst_rgba: Image.Image, src_rgba: Image.Image, xy: tuple[int,int]):
    """Paste only non-background pixels (background detected by floodfill from (0,0) on src)."""
    src = src_rgba.convert("RGBA")
    mask = bg_connected_mask(src)
    sw, sh = src.size
    sx, sy = xy
    dpx = dst_rgba.load()
    spx = src.load()
    for y in range(sh):
        for x in range(sw):
            if not mask[y][x]:
                r,g,b,a = spx[x,y]
                if a != 0:
                    dx, dy = sx+x, sy+y
                    if 0 <= dx < dst_rgba.size[0] and 0 <= dy < dst_rgba.size[1]:
                        dpx[dx,dy] = (r,g,b,255)

def quantize_foreground_to_15(canvas_rgba: Image.Image) -> Image.Image:
    """
    Returns a paletted (mode P) image where:
      - index 0 is reserved for background
      - indices 1..15 are used for colors
    """
    w, h = canvas_rgba.size
    px = canvas_rgba.load()

    # Build a temporary RGB image containing ONLY foreground pixels,
    # background pixels set to black (won't be sampled).
    fg = Image.new("RGB", (w,h), (0,0,0))
    fg_px = fg.load()
    fg_coords = []
    for y in range(h):
        for x in range(w):
            if px[x,y][3] != 0:  # alpha != 0
                fg_px[x,y] = px[x,y][:3]
                fg_coords.append((x,y))

    # Quantize foreground to 15 colors (no dithering).
    # If there are no foreground pixels, just return empty.
    if not fg_coords:
        out = Image.new("P", (w,h), 0)
        out.putpalette([0,0,0] + [0,0,0]*255)
        out.info["transparency"] = 0
        return out

    q = fg.quantize(colors=15, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)

    # Build final indexed image:
    # background = 0, foreground = q_index + 1
    out = Image.new("P", (w,h), 0)
    out_px = out.load()
    q_px = q.load()
    for (x,y) in fg_coords:
        out_px[x,y] = int(q_px[x,y]) + 1

    # Palette: index 0 can be anything; set it to magenta for debugging
    pal = [255,0,255]  # index 0
    qpal = q.getpalette()[:15*3]
    pal += qpal
    pal += [0,0,0] * (256 - (1+15))
    out.putpalette(pal)
    out.info["transparency"] = 0
    return out

def process_one(path: Path):
    src = Image.open(path).convert("RGBA")
    f0, f1 = extract_frames(src)

    # Build two 32x32 frames, centered (so your icon is the right size/position)
    top = Image.new("RGBA", (32,32), (0,0,0,0))
    bot = Image.new("RGBA", (32,32), (0,0,0,0))

    # Center source into 32x32 if it's smaller
    def centered_xy(im):
        return ((32 - im.size[0])//2, (32 - im.size[1])//2)

    paste_foreground(top, f0, centered_xy(f0))
    paste_foreground(bot, f1, centered_xy(f1))

    # Stack into 32x64
    canvas = Image.new("RGBA", (32,64), (0,0,0,0))
    canvas.paste(top, (0,0))
    canvas.paste(bot, (0,32))

    pal = quantize_foreground_to_15(canvas)
    out_path = OUT / path.name
    pal.save(out_path, optimize=True)

def main():
    for p in SRC.glob("*.png"):
        if p.is_file():
            process_one(p)
    print("Wrote:", OUT)

if __name__ == "__main__":
    raise SystemExit(main())
