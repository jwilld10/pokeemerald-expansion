#!/usr/bin/env python3
from pathlib import Path
import argparse
from PIL import Image

def gbapal_to_bgr555_list(gbapal_path: Path):
    data = gbapal_path.read_bytes()
    if len(data) < 32:
        raise SystemExit(f"ERROR: {gbapal_path} too small ({len(data)} bytes). Expected at least 32 bytes for 16 colors.")
    cols_5 = []
    for i in range(16):
        lo = data[i*2]
        hi = data[i*2+1]
        v = lo | (hi << 8)  # GBA BGR555
        b5 = (v >> 10) & 0x1F
        g5 = (v >> 5) & 0x1F
        r5 = (v >> 0) & 0x1F
        cols_5.append((r5, g5, b5))
    return cols_5

def expand5_to_8(x5: int) -> int:
    # Common GBA-style expansion (keeps 0->0, 31->255)
    return (x5 << 3) | (x5 >> 2)

def rgb8_to_5(r: int, g: int, b: int):
    # Round to nearest 5-bit (not floor)
    r5 = min(31, (r + 4) // 8)
    g5 = min(31, (g + 4) // 8)
    b5 = min(31, (b + 4) // 8)
    return (r5, g5, b5)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("png", type=Path)
    ap.add_argument("--gbapal", type=Path, default=None, help="Path to a 16-color .gbapal (defaults to sibling normal.gbapal)")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--strict", action="store_true", help="Fail if any non-transparent pixel doesn't map to palette in 5-bit space")
    args = ap.parse_args()

    png_path = args.png
    gbapal = args.gbapal if args.gbapal is not None else (png_path.parent / "normal.gbapal")
    if not gbapal.exists():
        raise SystemExit(f"ERROR: Missing palette: {gbapal}")

    pal5 = gbapal_to_bgr555_list(gbapal)

    # Build output palette (first 16 entries from gbapal, rest zeros)
    flat = []
    for (r5,g5,b5) in pal5:
        flat.extend([expand5_to_8(r5), expand5_to_8(g5), expand5_to_8(b5)])
    flat.extend([0,0,0] * (256 - 16))

    # Map 5-bit RGB -> index
    rgb5_to_idx = {}
    for i, key in enumerate(pal5):
        if key not in rgb5_to_idx:
            rgb5_to_idx[key] = i

    im = Image.open(png_path).convert("RGBA")
    w, h = im.size
    src = im.load()

    out = Image.new("P", (w, h), 0)
    out.putpalette(flat)
    out_px = out.load()

    bad = 0
    for y in range(h):
        for x in range(w):
            r,g,b,a = src[x,y]
            if a == 0:
                out_px[x,y] = 0
                continue

            key = rgb8_to_5(r,g,b)
            idx = rgb5_to_idx.get(key)
            if idx is None:
                bad += 1
                if args.strict:
                    raise SystemExit(
                        f"ERROR: Pixel not in palette (5-bit) at {png_path} ({x},{y}) rgb=({r},{g},{b}) rgb5={key}"
                    )
                # fallback: nearest in 5-bit space
                best_i = 0
                best_d = 10**18
                for i2,(rr,gg,bb) in enumerate(pal5):
                    d = (key[0]-rr)**2 + (key[1]-gg)**2 + (key[2]-bb)**2
                    if d < best_d:
                        best_d = d
                        best_i = i2
                idx = best_i

            out_px[x,y] = idx

    out.info["transparency"] = 0

    if args.apply:
        out.save(png_path, optimize=False)
        print(f"APPLIED: {png_path} -> PNG8 indexed using {gbapal} (bad_nonpal={bad})")
    else:
        print(f"CHECK: {png_path} would convert to PNG8 indexed using {gbapal} (bad_nonpal={bad})")

if __name__ == "__main__":
    main()
