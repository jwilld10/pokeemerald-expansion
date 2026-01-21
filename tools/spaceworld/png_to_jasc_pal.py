#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
from PIL import Image
import sys

def write_jasc(colors, out_path: Path):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="\n") as f:
        f.write("JASC-PAL\n")
        f.write("0100\n")
        f.write(f"{len(colors)}\n")
        for r,g,b in colors:
            f.write(f"{r} {g} {b}\n")

def main():
    if len(sys.argv) < 3:
        print("Usage: png_to_jasc_pal.py input.png output.pal [--pad16]", file=sys.stderr)
        return 2
    png = Path(sys.argv[1])
    out = Path(sys.argv[2])
    pad16 = "--pad16" in sys.argv[3:]

    im = Image.open(png).convert("RGBA")
    # Flatten transparency to black (gbagfx doesn’t like alpha)
    bg = Image.new("RGBA", im.size, (0,0,0,255))
    bg.alpha_composite(im)
    im = bg.convert("RGB")

    # Get palette by quantizing to 16 colors (stable order)
    q = im.quantize(colors=16, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette()[:16*3]
    colors = [(pal[i], pal[i+1], pal[i+2]) for i in range(0, len(pal), 3)]

    # Remove duplicates while preserving order
    seen = set()
    uniq = []
    for c in colors:
        if c not in seen:
            uniq.append(c)
            seen.add(c)

    if pad16 and len(uniq) < 16:
        uniq += [(0,0,0)] * (16 - len(uniq))

    # gbagfx expects 16 colors for 4bpp palettes in practice
    if len(uniq) > 16:
        uniq = uniq[:16]
    if len(uniq) < 16:
        uniq += [(0,0,0)] * (16 - len(uniq))

    write_jasc(uniq, out)
    print(f"Wrote {out} ({len(uniq)} colors)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
