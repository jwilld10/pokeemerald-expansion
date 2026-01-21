#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
from PIL import Image

ROOT = Path("graphics/spaceworld/pokemon")
BACKUP = Path("graphics/spaceworld/pokemon_padded_backup_pillow")
BACKUP.mkdir(parents=True, exist_ok=True)

BG = (255, 0, 255)  # background marker (will become palette index 0)
MAX_COLORS = 16

TARGET = (64, 64)
FILES = {"anim_front.png", "anim_frontf.png", "back.png"}

def ensure_palette_len(pal_list, entries=256):
    need = entries * 3
    if pal_list is None:
        pal_list = []
    if len(pal_list) < need:
        pal_list = pal_list + [0] * (need - len(pal_list))
    return pal_list

def force_bg_index0(pal_img: Image.Image) -> Image.Image:
    palette = ensure_palette_len(pal_img.getpalette(), 256)

    # find closest palette entry to BG among first MAX_COLORS
    best_i = 0
    best_d = 10**9
    for i in range(MAX_COLORS):
        pr, pg, pb = palette[3*i], palette[3*i+1], palette[3*i+2]
        d = (pr-BG[0])**2 + (pg-BG[1])**2 + (pb-BG[2])**2
        if d < best_d:
            best_d = d
            best_i = i

    if best_i == 0:
        pal_img.putpalette(palette)
        return pal_img

    # swap palette 0 <-> best_i
    p0 = palette[0:3]
    pi = palette[3*best_i:3*best_i+3]
    palette[0:3] = pi
    palette[3*best_i:3*best_i+3] = p0

    data = bytearray(pal_img.tobytes())
    for n, v in enumerate(data):
        if v == 0:
            data[n] = best_i
        elif v == best_i:
            data[n] = 0

    out = Image.frombytes("P", pal_img.size, bytes(data))
    out.putpalette(palette)
    return out

def process_one(p: Path):
    im = Image.open(p).convert("RGBA")
    w, h = im.size

    canvas = Image.new("RGBA", TARGET, (BG[0], BG[1], BG[2], 255))
    # CENTER it to fix off-center summary pics
    ox = (TARGET[0] - w) // 2
    oy = (TARGET[1] - h) // 2
    canvas.paste(im, (ox, oy), im)

    # Quantize to 16 colors, no dithering
    pal = canvas.convert("RGB").quantize(colors=MAX_COLORS, dither=Image.Dither.NONE)

    # Force BG to palette index 0 (for transparency behavior)
    pal = force_bg_index0(pal)

    pal.save(p, format="PNG", optimize=False)

def main():
    count = 0
    for mon_dir in sorted(ROOT.glob("*")):
        if not mon_dir.is_dir():
            continue
        for name in FILES:
            p = mon_dir / name
            if p.is_file():
                # backup once
                b = BACKUP / f"{mon_dir.name}__{name}"
                if not b.exists():
                    b.write_bytes(p.read_bytes())
                process_one(p)
                count += 1
    print(f"Padded+quantized {count} files to 64x64 PNG8")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
