#!/usr/bin/env python3
import argparse
from pathlib import Path
from PIL import Image
from collections import Counter

def most_common_opaque_rgba(img_rgba: Image.Image):
    data = img_rgba.getdata()
    c = Counter(px for px in data if px[3] != 0)
    if not c:
        return None
    return c.most_common(1)[0][0]

def remove_bg_color(img_rgba: Image.Image, bg_rgba):
    if bg_rgba is None:
        return img_rgba
    br,bg,bb,ba = bg_rgba
    data = img_rgba.getdata()
    out = []
    for r,g,b,a in data:
        if a != 0 and (r,g,b,a) == (br,bg,bb,ba):
            out.append((0,0,0,0))
        else:
            out.append((r,g,b,a))
    res = Image.new("RGBA", img_rgba.size)
    res.putdata(out)
    return res

def bbox_of_ink(img_rgba: Image.Image):
    alpha = img_rgba.split()[3]
    return alpha.getbbox()

def center_on_canvas(img_rgba: Image.Image, canvas: int):
    bbox = bbox_of_ink(img_rgba)
    if bbox is None:
        return Image.new("RGBA", (canvas, canvas), (0,0,0,0))
    ink = img_rgba.crop(bbox)
    iw, ih = ink.size
    out = Image.new("RGBA", (canvas, canvas), (0,0,0,0))
    x = (canvas - iw) // 2
    y = (canvas - ih) // 2
    out.alpha_composite(ink, (x, y))
    return out

def to_png8_trans0(img_rgba: Image.Image) -> Image.Image:
    """
    Convert RGBA -> paletted PNG8 with transparency index 0.
    Minimize color changes by quantizing to 16 colors, no dithering.
    """
    # If everything is already simple (mostly black/white/gray), this stays stable.
    q = img_rgba.quantize(colors=16, method=Image.FASTOCTREE, dither=Image.Dither.NONE)

    # Ensure transparency exists and is index 0.
    # PIL stores transparency as an index in info['transparency'] for P images.
    # We'll force transparent pixels to 0, then rotate palette so 0 is transparent.
    pal = q.getpalette()
    data = list(q.getdata())

    # Create mask of transparency from original alpha
    alpha = img_rgba.split()[3].getdata()
    for i, a in enumerate(alpha):
        if a == 0:
            data[i] = 0

    # Now we need to ensure index 0 represents a transparent color in the palette.
    # Put (0,0,0) at palette slot 0 (fine, since it will be transparent anyway).
    pal[0:3] = [0,0,0]

    out = Image.new("P", q.size)
    out.putpalette(pal)
    out.putdata(data)
    out.info["transparency"] = 0
    return out

def process(path: Path, canvas: int, apply: bool):
    orig = Image.open(path)
    img = orig.convert("RGBA")

    # Key step: background is usually the MOST COMMON opaque color (your purple box).
    bg = most_common_opaque_rgba(img)
    img = remove_bg_color(img, bg)
    img = center_on_canvas(img, canvas)

    out = to_png8_trans0(img)

    if apply:
        out.save(path, "PNG", optimize=False)
        return True
    return False

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="graphics/spaceworld/pokemon")
    ap.add_argument("--glob", default="**/anim_*.png")
    ap.add_argument("--canvas", type=int, default=64)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    root = Path(args.root)
    paths = sorted(root.glob(args.glob))
    if not paths:
        raise SystemExit(f"No files matched {args.glob} under {root}")

    print(f"{'APPLY' if args.apply else 'DRY'}: {len(paths)} files")
    for p in paths:
        changed = process(p, args.canvas, args.apply)
        print(("FIX " if changed else "CHK ") + str(p))

    if not args.apply:
        print("Dry-run done. Re-run with --apply to write changes.")

if __name__ == "__main__":
    main()
