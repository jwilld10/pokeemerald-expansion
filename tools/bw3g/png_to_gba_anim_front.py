#!/usr/bin/env python3
import sys, os, math
from pathlib import Path
from PIL import Image

# -------- LZ77 (GBA) compressor (works, small, deterministic) --------
# This is a simple LZ77(0x10) encoder. Good enough for assets.
def lz77_compress(raw: bytes) -> bytes:
    out = bytearray()
    out += b'\x10'
    out += (len(raw)).to_bytes(3, 'little')
    i = 0
    # naive sliding window
    while i < len(raw):
        flag_pos = len(out)
        out.append(0)
        flags = 0
        for b in range(8):
            if i >= len(raw):
                break
            best_len = 0
            best_dist = 0
            start = max(0, i - 0x1000)
            # search backwards
            for j in range(i - 1, start - 1, -1):
                dist = i - j
                if dist > 0x1000:
                    break
                k = 0
                while k < 18 and i + k < len(raw) and raw[j + k] == raw[i + k]:
                    k += 1
                if k > best_len and k >= 3:
                    best_len = k
                    best_dist = dist
                    if best_len == 18:
                        break
            if best_len >= 3:
                flags |= (1 << (7 - b))
                # len encoded as (len-3) in top nibble, dist-1 in 12 bits
                token = ((best_len - 3) << 12) | (best_dist - 1)
                out += token.to_bytes(2, 'big')
                i += best_len
            else:
                out.append(raw[i])
                i += 1
        out[flag_pos] = flags
    return bytes(out)

# -------- GBA 4bpp tiling (8x8 tiles, row-major tiles) --------
def to_4bpp_tiled(indices, w, h) -> bytes:
    # indices: list of ints 0..15 length w*h
    assert w % 8 == 0 and h % 8 == 0
    out = bytearray()
    tiles_x = w // 8
    tiles_y = h // 8
    for ty in range(tiles_y):
        for tx in range(tiles_x):
            for y in range(8):
                row = []
                base = (ty * 8 + y) * w + (tx * 8)
                row = indices[base:base+8]
                # pack into 4 bytes (two pixels per byte, low nibble first)
                for x in range(0, 8, 2):
                    a = row[x] & 0xF
                    b = row[x+1] & 0xF
                    out.append(a | (b << 4))
    return bytes(out)

def pad_center(img_rgba: Image.Image, canvas=64) -> Image.Image:
    w, h = img_rgba.size
    if w > canvas or h > canvas:
        raise ValueError(f"Image {w}x{h} larger than canvas {canvas}x{canvas}")
    out = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    x = (canvas - w) // 2
    y = (canvas - h) // 2
    out.paste(img_rgba, (x, y))
    return out

def split_frames(img_rgba: Image.Image):
    img_rgba = img_rgba.convert("RGBA")
    w, h = img_rgba.size

    # If it's already reasonable, treat as single-frame
    if w <= 64 and h <= 64:
        return [img_rgba]

    # Vertical strip Wx(W*n)
    if w <= 64 and h % w == 0:
        n = h // w
        frames = [img_rgba.crop((0, i*w, w, (i+1)*w)) for i in range(n)]
        return frames

    # Horizontal strip (H*n)xH
    if h <= 64 and w % h == 0:
        n = w // h
        frames = [img_rgba.crop((i*h, 0, (i+1)*h, h)) for i in range(n)]
        return frames

    # 64x(64*n) or (64*n)x64
    if w == 64 and h % 64 == 0:
        n = h // 64
        frames = [img_rgba.crop((0, i*64, 64, (i+1)*64)) for i in range(n)]
        return frames
    if h == 64 and w % 64 == 0:
        n = w // 64
        frames = [img_rgba.crop((i*64, 0, (i+1)*64, 64)) for i in range(n)]
        return frames

    # Fallback: take a centered crop as 1 frame
    left = max(0, (w - 64)//2)
    top  = max(0, (h - 64)//2)
    return [img_rgba.crop((left, top, left+64, top+64))]

def choose_4_frames(frames):
    # Engine-friendly: exactly 4 frames
    if len(frames) == 1:
        return frames * 4
    if len(frames) == 2:
        return [frames[0], frames[1], frames[0], frames[1]]
    if len(frames) == 3:
        return [frames[0], frames[1], frames[2], frames[1]]
    # >= 4: sample evenly across the strip
    idxs = [0, (len(frames)-1)//3, (2*(len(frames)-1))//3, len(frames)-1]
    return [frames[i] for i in idxs]

def build_palette_and_index(frames64):
    # Reserve index 0 for transparency ONLY.
    # Quantize opaque pixels into 15 colors, then shift by +1.
    # This prevents "white became transparent" unless white was literally transparent.
    canv = Image.new("RGBA", (64*len(frames64), 64), (0,0,0,0))
    for i,f in enumerate(frames64):
        canv.paste(f, (i*64, 0))

    rgba = canv.convert("RGBA")
    data = rgba.getdata()

    # Build an RGB image from opaque pixels only (transparent -> black placeholder)
    rgb = Image.new("RGB", rgba.size, (0,0,0))
    rgb_px = []
    for (r,g,b,a) in data:
        if a >= 128:
            rgb_px.append((r,g,b))
        else:
            rgb_px.append((0,0,0))
    rgb.putdata(rgb_px)

    # Quantize to 15 colors (we'll add transparency as color 0)
    q = rgb.quantize(colors=15, method=2)  # FASTOCTREE supports RGBA-origin workflows safely
    pal = q.getpalette()[:15*3]  # 15 colors

    # Make full 16-color palette with entry0 = black (transparent index)
    # (actual transparency is handled by index0, not alpha in pal)
    full_pal = [0,0,0] + pal
    full_pal += [0,0,0] * (16 - len(full_pal)//3)

    # Now map each frame: transparent->0, opaque->q_index+1
    q_idx = list(q.getdata())
    out_frames_idx = []
    for fi in range(len(frames64)):
        idx = []
        for y in range(64):
            for x in range(64):
                r,g,b,a = frames64[fi].getpixel((x,y))
                if a < 128:
                    idx.append(0)
                else:
                    # read from quantized canvas at same location
                    canvas_x = fi*64 + x
                    qi = q_idx[y*rgb.size[0] + canvas_x]
                    # qi in 0..14 => shift to 1..15
                    idx.append(int(qi) + 1)
        out_frames_idx.append(idx)

    return full_pal, out_frames_idx

def write_gbapal(pal_rgb, out_path):
    # Convert 16*RGB (0..255) to GBA BGR555
    def to_bgr555(r,g,b):
        R = (r >> 3) & 31
        G = (g >> 3) & 31
        B = (b >> 3) & 31
        return (B << 10) | (G << 5) | R

    b = bytearray()
    for i in range(16):
        r = pal_rgb[i*3+0]
        g = pal_rgb[i*3+1]
        bl= pal_rgb[i*3+2]
        v = to_bgr555(r,g,bl)
        b += v.to_bytes(2, "little")
    Path(out_path).write_bytes(bytes(b))

def main():
    if len(sys.argv) != 5:
        print("usage: png_to_gba_anim_front.py FRONT_PNG BACK_PNG OUTDIR MONNAME", file=sys.stderr)
        sys.exit(2)

    front_png = Path(sys.argv[1])
    back_png  = Path(sys.argv[2])
    outdir    = Path(sys.argv[3])
    monname   = sys.argv[4]

    outdir.mkdir(parents=True, exist_ok=True)

    # --- FRONT (animated) ---
    front_img = Image.open(front_png).convert("RGBA")
    frames = split_frames(front_img)
    frames = choose_4_frames(frames)
    frames64 = [pad_center(f, 64) for f in frames]

    pal_rgb, frames_idx = build_palette_and_index(frames64)

    raw_front = b""
    for idx in frames_idx:
        raw_front += to_4bpp_tiled(idx, 64, 64)

    front_lz = lz77_compress(raw_front)
    (outdir / "anim_front.4bpp.lz").write_bytes(front_lz)

    # --- BACK (static, still 64x64 padded) ---
    back_img = Image.open(back_png).convert("RGBA")
    back_frames = split_frames(back_img)
    back_frame = back_frames[0]
    back64 = pad_center(back_frame, 64)

    # reuse SAME palette to avoid palette mismatch artifacts
    back_idx = []
    # remap back pixels to nearest palette entry (1..15), transparency->0
    # simple nearest RGB search (fast enough for 64x64)
    pal = [(pal_rgb[i*3], pal_rgb[i*3+1], pal_rgb[i*3+2]) for i in range(16)]
    def nearest(r,g,b):
        best = 1
        bestd = 10**18
        for i in range(1,16):
            pr,pg,pb = pal[i]
            d = (r-pr)*(r-pr)+(g-pg)*(g-pg)+(b-pb)*(b-pb)
            if d < bestd:
                bestd = d
                best = i
        return best

    for y in range(64):
        for x in range(64):
            r,g,b,a = back64.getpixel((x,y))
            if a < 128:
                back_idx.append(0)
            else:
                back_idx.append(nearest(r,g,b))

    raw_back = to_4bpp_tiled(back_idx, 64, 64)
    back_lz = lz77_compress(raw_back)
    (outdir / "back.4bpp.lz").write_bytes(back_lz)

    # --- PALETTE ---
    write_gbapal(pal_rgb, outdir / "normal.gbapal")

    print(f"OK: {monname} frames={len(frames)} -> anim_front.4bpp.lz + back.4bpp.lz + normal.gbapal")

if __name__ == "__main__":
    main()
