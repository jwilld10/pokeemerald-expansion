#!/usr/bin/env python3
import argparse
from pathlib import Path
from collections import Counter
from PIL import Image

def border_indices(pix, w, h):
    # one-pixel border
    for x in range(w):
        yield pix[x, 0]
        yield pix[x, h-1]
    for y in range(1, h-1):
        yield pix[0, y]
        yield pix[w-1, y]

def swap_palette_index0(imP: Image.Image, idx: int) -> Image.Image:
    # swap palette entry idx <-> 0 and remap pixels accordingly (no recolor)
    data = bytearray(imP.tobytes())
    for i, v in enumerate(data):
        if v == 0:
            data[i] = idx
        elif v == idx:
            data[i] = 0

    pal = imP.getpalette()
    if pal is None:
        raise RuntimeError("missing palette")
    a3, b3 = 0, idx * 3
    pal[a3:a3+3], pal[b3:b3+3] = pal[b3:b3+3], pal[a3:a3+3]

    out = Image.frombytes("P", imP.size, bytes(data))
    out.putpalette(pal)
    out.info["transparency"] = 0
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("png", help="PNG8 (mode P) file")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--to-index0", action="store_true",
                    help="After choosing bg index, swap it into palette index 0 (GBA-friendly).")
    ap.add_argument("--force", action="store_true",
                    help="Proceed even if bg index is used inside (can create holes).")
    args = ap.parse_args()

    p = Path(args.png)
    im = Image.open(p)

    if im.mode != "P":
        raise SystemExit(f"ERROR: {p}: not PNG8 (mode P). Refusing to quantize/recolor.")

    w, h = im.size
    pix = im.load()

    # pick most common palette index along the outer border
    counts = Counter(border_indices(pix, w, h))
    bg_idx, bg_count = counts.most_common(1)[0]

    # If transparency already exists, don't override unless user really wants it
    if "transparency" in im.info:
        raise SystemExit(f"ERROR: {p}: already has transparency chunk (index={im.info['transparency']}).")

    # Safety check: ensure bg index isn't used heavily in the interior
    # (If it is, making it transparent will punch holes.)
    interior = 0
    interior_bg = 0
    for y in range(1, h-1):
        for x in range(1, w-1):
            interior += 1
            if pix[x, y] == bg_idx:
                interior_bg += 1

    # If bg index appears in interior, it might be a real sprite color.
    # Allow a tiny amount (noise), but otherwise refuse unless --force.
    if interior_bg > 0 and not args.force:
        # threshold: more than 0.2% of interior pixels using bg index
        if interior_bg / max(1, interior) > 0.002:
            raise SystemExit(
                f"ERROR: {p}: chosen bg index {bg_idx} appears inside sprite "
                f"({interior_bg}/{interior} interior px). "
                f"Refusing to avoid holes. Use --force if you're sure."
            )

    out = im.copy()
    out.info["transparency"] = bg_idx

    if args.to_index0:
        out = swap_palette_index0(out, bg_idx)

    if args.apply:
        out.save(p)

    print(f"{'APPLIED' if args.apply else 'DRY'}: {p}")
    print(f"  picked bg index: {bg_idx} (border px count {bg_count})")
    print(f"  interior usage of bg index: {interior_bg}/{interior}")
    print(f"  wrote transparency: {'index0' if args.to_index0 else bg_idx}")

if __name__ == "__main__":
    main()
