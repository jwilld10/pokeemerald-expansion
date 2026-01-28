#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
from datetime import datetime
import struct
from PIL import Image, ImageSequence

W, H = 32, 32
OUT_W, OUT_H = 32, 64

def bgr555_to_rgb(c: int):
    r = (c & 0x1F) << 3
    g = ((c >> 5) & 0x1F) << 3
    b = ((c >> 10) & 0x1F) << 3
    return (r, g, b)

def load_gbapal(path: Path):
    cols = struct.unpack("<16H", path.read_bytes()[:32])
    return [bgr555_to_rgb(c) for c in cols]

def nearest_palette_index(rgb, pal_rgb):
    # 0 is reserved transparent; we still allow mapping to 0 if pixel is fully transparent
    r,g,b = rgb
    best_i = 1
    best_d = 10**18
    for i in range(1, 16):
        pr,pg,pb = pal_rgb[i]
        d = (r-pr)*(r-pr) + (g-pg)*(g-pg) + (b-pb)*(b-pb)
        if d < best_d:
            best_d = d
            best_i = i
    return best_i

def force_32x32_no_resample(im: Image.Image) -> Image.Image:
    # Convert to RGBA first
    im = im.convert("RGBA")
    src_w, src_h = im.size
    out = Image.new("RGBA", (W, H), (0,0,0,0))
    # Paste at top-left and crop if larger; pad if smaller.
    out.paste(im, (0,0))
    if src_w > W or src_h > H:
        out = out.crop((0,0,W,H))
    return out

def frame_indices(im: Image.Image, pal_rgb):
    # Returns a 32x32 grid of palette indices (0..15)
    px = im.load()
    idx = [[0]*W for _ in range(H)]
    for y in range(H):
        for x in range(W):
            r,g,b,a = px[x,y]
            if a < 8:
                idx[y][x] = 0
            else:
                idx[y][x] = nearest_palette_index((r,g,b), pal_rgb)
    return idx

def write_gba_4bpp_tiled(path: Path, idx64):
    # idx64 is 64 rows x 32 cols
    out = bytearray()
    # tiles: 8x8, row-major over tiles
    for ty in range(OUT_H//8):          # 8 tiles high
        for tx in range(OUT_W//8):      # 4 tiles wide
            for row in range(8):
                y = ty*8 + row
                x0 = tx*8
                for x in range(0, 8, 2):
                    a = idx64[y][x0+x] & 0xF
                    b = idx64[y][x0+x+1] & 0xF
                    out.append(a | (b<<4))
    path.write_bytes(out)

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--gifdir", required=True, help="Folder with reference GIFs")
    ap.add_argument("--outdir", required=True, help="Output folder for .4bpp")
    ap.add_argument("--gbapal", required=True, help="Spaceworld .gbapal (16-color) file")
    ap.add_argument("--apply", action="store_true", help="Write outputs (default: dry-run)")
    args = ap.parse_args()

    gifdir = Path(args.gifdir)
    outdir = Path(args.outdir)
    pal = load_gbapal(Path(args.gbapal))
    if len(pal) < 16:
        pal = pal + [(0,0,0)]*(16-len(pal))

    gifs = sorted(gifdir.glob("*.gif"))
    if not gifs:
        raise SystemExit(f"No GIFs found in {gifdir}")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = outdir.parent / f"_icon_backups_fromgif_{ts}"

    print("GIFs:", len(gifs))
    print("Mode:", "APPLY" if args.apply else "DRY-RUN")
    if args.apply:
        outdir.mkdir(parents=True, exist_ok=True)
        backup_dir.mkdir(parents=True, exist_ok=True)
        print("Backups:", backup_dir)

    for g in gifs:
        im = Image.open(g)
        frames = [f.copy() for f in ImageSequence.Iterator(im)]
        if len(frames) == 0:
            print("SKIP (no frames):", g.name)
            continue

        f0 = force_32x32_no_resample(frames[0])
        f1 = force_32x32_no_resample(frames[1] if len(frames) > 1 else frames[0])

        idx0 = frame_indices(f0, pal)
        idx1 = frame_indices(f1, pal)

        idx64 = idx0 + idx1  # 64 rows

        out = outdir / (g.stem.lower().replace("pokegoldfinal-ms","").replace("-","_") + ".4bpp")

        if args.apply and out.exists():
            (backup_dir / out.name).write_bytes(out.read_bytes())

        print(("WRITE" if args.apply else "WOULD WRITE"), out.name, "<-", g.name)
        if args.apply:
            write_gba_4bpp_tiled(out, idx64)

    if args.apply:
        print("Done. Outputs in", outdir)

if __name__ == "__main__":
    main()
