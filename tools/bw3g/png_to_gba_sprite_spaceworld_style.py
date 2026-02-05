#!/usr/bin/env python3
import os, sys, re, struct
from PIL import Image

# ----------------------------
# GBA LZ77 compressor (0x10)
# ----------------------------
def gba_lz77_compress(data: bytes) -> bytes:
    # Standard GBA LZ77 (type 0x10). This is not "optimal" but is valid.
    out = bytearray()
    out.append(0x10)
    out += struct.pack("<I", len(data))[0:3]

    i = 0
    n = len(data)

    # Simple sliding window search
    # window: up to 0x1000 back, match len 3..18
    while i < n:
        flag_pos = len(out)
        out.append(0)  # flags byte placeholder
        flags = 0

        for bit in range(8):
            if i >= n:
                break

            best_len = 0
            best_disp = 0

            win_start = max(0, i - 0x1000)
            max_len = min(18, n - i)

            # Quick path: if fewer than 3 bytes remain, must be literal
            if max_len >= 3:
                # naive search from i-1 down to win_start
                # (good enough for tooling)
                for j in range(i - 1, win_start - 1, -1):
                    # maximum possible match length at j
                    k = 0
                    while k < max_len and data[j + k] == data[i + k]:
                        k += 1
                    if k > best_len and k >= 3:
                        best_len = k
                        best_disp = i - j
                        if best_len == 18:
                            break

            if best_len >= 3:
                # compressed block
                flags |= (1 << (7 - bit))
                disp = best_disp - 1  # 0..4095
                ln = best_len - 3     # 0..15
                token = ((ln & 0xF) << 12) | (disp & 0xFFF)
                out += struct.pack(">H", token)
                i += best_len
            else:
                # literal
                out.append(data[i])
                i += 1

        out[flag_pos] = flags

    # Pad to 4 bytes so INCBIN_U32 is always safe
    while len(out) % 4 != 0:
        out.append(0)

    return bytes(out)

# ----------------------------
# Palette + tiling helpers
# ----------------------------
def rgba_to_rgb(img: Image.Image) -> Image.Image:
    if img.mode == "RGBA":
        bg = Image.new("RGB", img.size, (0, 0, 0))
        bg.paste(img, mask=img.split()[3])
        return bg
    return img.convert("RGB")

def make_transparency_mask(img_rgba: Image.Image) -> Image.Image:
    # alpha==0 => transparent
    if img_rgba.mode != "RGBA":
        img_rgba = img_rgba.convert("RGBA")
    a = img_rgba.split()[3]
    # mask is 255 where alpha==0
    return a.point(lambda v: 255 if v == 0 else 0)

def quantize_15_colors(rgb_img: Image.Image) -> Image.Image:
    # Quantize to 15 colors (no alpha) using FASTOCTREE.
    # (Pillow requires method 2 or 3 for RGBA; we avoid RGBA entirely here.)
    return rgb_img.quantize(colors=15, method=Image.FASTOCTREE)

def build_palette_16(q15: Image.Image) -> bytes:
    # q15 palette has up to 15 entries; we will prepend transparent entry at index 0.
    pal = q15.getpalette()[:15*3]
    # index0 = transparent "key" color (doesn't matter, because pixels are 0 only for transparent)
    pal16 = [(0, 0, 0)]
    for i in range(15):
        r, g, b = pal[i*3+0], pal[i*3+1], pal[i*3+2]
        pal16.append((r, g, b))

    # Convert RGB888 -> BGR555 little endian
    out = bytearray()
    for (r, g, b) in pal16:
        r5 = (r * 31 + 127) // 255
        g5 = (g * 31 + 127) // 255
        b5 = (b * 31 + 127) // 255
        val = (r5) | (g5 << 5) | (b5 << 10)
        out += struct.pack("<H", val)
    return bytes(out)

def apply_palette_and_indices(q15: Image.Image, transparent_mask: Image.Image) -> bytes:
    # q15 pixels are 0..14; we need final pixels:
    #   transparent => 0
    #   opaque => q15_index+1 (so real colors never use 0)
    w, h = q15.size
    qpx = q15.load()
    mpx = transparent_mask.load()
    idx = bytearray(w*h)
    for y in range(h):
        for x in range(w):
            if mpx[x, y] == 255:
                idx[y*w + x] = 0
            else:
                idx[y*w + x] = qpx[x, y] + 1
    return bytes(idx)

def to_4bpp_tiled(indices: bytes, w: int, h: int) -> bytes:
    # GBA expects 8x8 tiles stored left->right, top->bottom.
    # Within each tile: rows 0..7, and within row: pixels packed 2 per byte (low nibble first).
    assert w % 8 == 0 and h % 8 == 0, "Canvas must be multiple of 8"
    out = bytearray()
    for ty in range(0, h, 8):
        for tx in range(0, w, 8):
            for y in range(8):
                row = (ty + y) * w + tx
                for x in range(0, 8, 2):
                    p0 = indices[row + x] & 0xF
                    p1 = indices[row + x + 1] & 0xF
                    out.append(p0 | (p1 << 4))
    return bytes(out)

def crop_or_pad(img: Image.Image, cw: int, ch: int) -> Image.Image:
    # If img is larger (like a strip/sheet), crop top-left cw x ch (safe, deterministic).
    # If smaller, paste it at center of canvas with transparent background.
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    w, h = img.size
    if w >= cw and h >= ch:
        return img.crop((0, 0, cw, ch))
    canvas = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    ox = (cw - w) // 2
    oy = (ch - h) // 2
    canvas.paste(img, (ox, oy))
    return canvas

def convert_one(png_path: str, out_lz: str, out_pal: str, cw: int, ch: int):
    img = Image.open(png_path).convert("RGBA")
    img = crop_or_pad(img, cw, ch)

    # Build transparency mask from alpha==0
    tmask = make_transparency_mask(img)

    # Quantize ONLY opaque colors to 15 colors (no alpha)
    rgb = rgba_to_rgb(img)
    q15 = quantize_15_colors(rgb)

    pal16 = build_palette_16(q15)
    indices = apply_palette_and_indices(q15, tmask)
    raw4 = to_4bpp_tiled(indices, cw, ch)
    lz = gba_lz77_compress(raw4)

    os.makedirs(os.path.dirname(out_lz), exist_ok=True)
    with open(out_lz, "wb") as f:
        f.write(lz)
    with open(out_pal, "wb") as f:
        f.write(pal16)

def main():
    if len(sys.argv) != 7:
        print("usage: png_to_gba_sprite_spaceworld_style.py <front_png> <back_png> <outdir> <frontWxH> <backWxH> <monname>", file=sys.stderr)
        sys.exit(2)

    front_png, back_png, outdir, fwh, bwh, mon = sys.argv[1:]
    fw, fh = map(int, fwh.lower().split("x"))
    bw, bh = map(int, bwh.lower().split("x"))

    # Force multiples of 8 (engine pics are tile-based)
    if fw % 8 != 0 or fh % 8 != 0 or bw % 8 != 0 or bh % 8 != 0:
        raise ValueError(f"{mon}: sizes must be multiples of 8 (got front {fw}x{fh}, back {bw}x{bh})")

    convert_one(front_png, os.path.join(outdir, "front.4bpp.lz"), os.path.join(outdir, "normal.gbapal"), fw, fh)
    convert_one(back_png,  os.path.join(outdir, "back.4bpp.lz"),  os.path.join(outdir, "normal.gbapal"), bw, bh)

if __name__ == "__main__":
    main()
