#!/usr/bin/env python3
import os, re, sys
from pathlib import Path
from PIL import Image

# ---------------- LZ77 (GBA 0x10) ----------------
def lz77_compress_gba(data: bytes) -> bytes:
    # Simple greedy compressor. Good enough for build assets.
    out = bytearray()
    out.append(0x10)
    out += len(data).to_bytes(3, "little")
    i = 0
    n = len(data)
    while i < n:
        flag_pos = len(out)
        out.append(0)  # placeholder
        flags = 0
        for bit in range(8):
            if i >= n:
                break
            best_len = 0
            best_disp = 0
            # search window max 0x1000 back
            win_start = max(0, i - 0x1000)
            # max match length 18
            max_len = min(18, n - i)
            # naive search (acceptable for sprite sizes)
            for j in range(i - 1, win_start - 1, -1):
                disp = i - j
                if disp > 0x1000:
                    break
                l = 0
                while l < max_len and data[j + l] == data[i + l]:
                    l += 1
                if l > best_len and l >= 3:
                    best_len = l
                    best_disp = disp
                    if best_len == 18:
                        break
            if best_len >= 3:
                flags |= (1 << (7 - bit))
                length = best_len - 3
                disp = best_disp - 1
                out.append(((length & 0xF) << 4) | ((disp >> 8) & 0xF))
                out.append(disp & 0xFF)
                i += best_len
            else:
                out.append(data[i])
                i += 1
        out[flag_pos] = flags
    return bytes(out)

# ---------------- Parsing sizes from bw3g_families.h ----------------
SIZE_RE = re.compile(
    r"gMonFrontPic_([A-Z0-9_]+)Bw3g.*?\.frontPicSize\s*=\s*MON_COORDS_SIZE\(\s*(\d+)\s*,\s*(\d+)\s*\).*?"
    r"gMonBackPic_\1Bw3g.*?\.backPicSize\s*=\s*MON_COORDS_SIZE\(\s*(\d+)\s*,\s*(\d+)\s*\)",
    re.S
)

def parse_sizes(fams_text: str):
    sizes = {}
    for m in SIZE_RE.finditer(fams_text):
        key = m.group(1).lower()
        fw, fh, bw, bh = map(int, m.group(2,3,4,5))
        sizes[key] = (fw, fh, bw, bh)
    return sizes

# ---------------- Image -> 4bpp tiled with transparency-safe palette ----------------
def rgb_to_bgr555(rgb):
    r, g, b = rgb
    return ((b >> 3) << 10) | ((g >> 3) << 5) | (r >> 3)

def build_palette_and_indices(img_rgba: Image.Image):
    # Treat alpha==0 as transparent ONLY.
    # Build palette from opaque pixels only (max 15 colors), then prepend index0.
    px = img_rgba.getdata()
    opaque = [p[:3] for p in px if p[3] != 0]
    if not opaque:
        # all transparent: palette 0 + 15 dummy
        pal = [(0,0,0)] * 16
        idx = [0] * (img_rgba.width * img_rgba.height)
        return pal, idx

    # Quantize opaque colors to 15 using an RGB image (no alpha), then map back.
    rgb = Image.new("RGB", img_rgba.size, (0,0,0))
    rgb.putdata([p[:3] for p in px])  # alpha ignored, but we'll force transparent later

    # PIL only allows quantize RGBA with method 2 or 3; we quantize RGB to be safe.
    q = rgb.quantize(colors=15, method=2)  # fast octree
    pal_raw = q.getpalette()[:15*3]
    pal15 = [(pal_raw[i], pal_raw[i+1], pal_raw[i+2]) for i in range(0, len(pal_raw), 3)]
    pal16 = [(0,0,0)] + pal15[:15]

    q_idx = list(q.getdata())  # 0..14
    out_idx = []
    for (r,g,b,a), qi in zip(px, q_idx):
        if a == 0:
            out_idx.append(0)
        else:
            # shift up by 1 so opaque never uses index0
            out_idx.append(min(15, qi + 1))
    return pal16, out_idx

def pad_to_canvas(img, canvas_w, canvas_h):
    w, h = img.size
    if w > canvas_w or h > canvas_h:
        raise ValueError(f"Image {w}x{h} larger than canvas {canvas_w}x{canvas_h}")
    out = Image.new("RGBA", (canvas_w, canvas_h), (0,0,0,0))
    # center horizontally, bottom-align like many mon sprites (helps reduce top peeking)
    x = (canvas_w - w) // 2
    y = canvas_h - h
    out.alpha_composite(img, (x, y))
    return out

def indices_to_4bpp_tiled(indices, w, h):
    # GBA sprite tile order: 8x8 tiles left-to-right, top-to-bottom
    # Each tile is 32 bytes (4bpp). Each byte stores two pixels (low/high nibble).
    out = bytearray()
    tiles_x = (w + 7) // 8
    tiles_y = (h + 7) // 8
    for ty in range(tiles_y):
        for tx in range(tiles_x):
            for row in range(8):
                y = ty*8 + row
                for col in range(0, 8, 2):
                    x0 = tx*8 + col
                    x1 = x0 + 1
                    p0 = 0
                    p1 = 0
                    if y < h and x0 < w:
                        p0 = indices[y*w + x0] & 0xF
                    if y < h and x1 < w:
                        p1 = indices[y*w + x1] & 0xF
                    out.append(p0 | (p1 << 4))
    return bytes(out)

def write_gbapal(pal16, out_path: Path):
    b = bytearray()
    for rgb in pal16:
        b += int(rgb_to_bgr555(rgb)).to_bytes(2, "little")
    out_path.write_bytes(bytes(b))

def convert_one(png_path: Path, out_4bpp_lz: Path, out_pal: Path, w: int, h: int):
    img = Image.open(png_path).convert("RGBA")
    # make a 64x64 canvas, but only the top-left (0,0) .. (w,h) portion will be used by engine via MON_COORDS_SIZE.
    canvas = pad_to_canvas(img, 64, 64)

    pal16, idx = build_palette_and_indices(canvas)
    raw = indices_to_4bpp_tiled(idx, 64, 64)
    out_4bpp_lz.write_bytes(lz77_compress_gba(raw))
    write_gbapal(pal16, out_pal)

def main():
    if len(sys.argv) != 4:
        print("usage: png_to_gba_sprite_spaceworld_v2.py <png_root> <families_h> <out_root>")
        sys.exit(2)

    png_root = Path(sys.argv[1])
    fams = Path(sys.argv[2]).read_text(encoding="utf-8", errors="replace")
    out_root = Path(sys.argv[3])

    sizes = parse_sizes(fams)
    if not sizes:
        print("ERROR: parsed 0 size entries from bw3g_families.h")
        sys.exit(1)

    converted = 0
    skipped = 0
    missing_size = 0
    missing_png = 0
    too_big = 0

    for mon_dir in sorted([p for p in png_root.iterdir() if p.is_dir()]):
        name = mon_dir.name.lower()
        front = mon_dir / "front.png"
        back  = mon_dir / "back.png"

        if name not in sizes:
            # allow "genesis" / placeholder folders to exist without sizes
            skipped += 1
            missing_size += 1
            continue
        if not front.exists() or not back.exists():
            skipped += 1
            missing_png += 1
            continue

        fw, fh, bw, bh = sizes[name]
        outdir = out_root / name
        outdir.mkdir(parents=True, exist_ok=True)
        try:
            convert_one(front, outdir/"front.4bpp.lz", outdir/"normal.gbapal", fw, fh)
            convert_one(back,  outdir/"back.4bpp.lz",  outdir/"normal.gbapal", bw, bh)
        except ValueError as e:
            skipped += 1
            too_big += 1
            continue

        converted += 1

    print(f"DONE. converted={converted} skipped={skipped} (missing_size={missing_size} missing_png={missing_png} too_big={too_big})")

if __name__ == "__main__":
    main()
