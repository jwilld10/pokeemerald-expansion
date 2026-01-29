#!/usr/bin/env python3
import argparse
from pathlib import Path
from PIL import Image
from collections import Counter

def infer_bg_color(img_rgba: Image.Image):
    """
    Infer background color by sampling corners and picking the most common.
    Works well for 'purple box' or other solid matte backgrounds.
    """
    px = img_rgba.load()
    w, h = img_rgba.size
    samples = [
        px[0,0], px[w-1,0], px[0,h-1], px[w-1,h-1],
        px[w//2, 0], px[w//2, h-1], px[0, h//2], px[w-1, h//2],
    ]
    # If any already transparent, prefer that (means image already has alpha bg)
    if any(s[3] == 0 for s in samples):
        return None
    return Counter(samples).most_common(1)[0][0]  # (r,g,b,a)

def make_bg_transparent(img_rgba: Image.Image, bg_rgba):
    if bg_rgba is None:
        return img_rgba
    data = img_rgba.getdata()
    new = []
    br, bg, bb, ba = bg_rgba
    for (r,g,b,a) in data:
        # exact match -> transparent
        if (r,g,b,a) == (br,bg,bb,ba):
            new.append((0,0,0,0))
        else:
            new.append((r,g,b,a))
    out = Image.new("RGBA", img_rgba.size)
    out.putdata(new)
    return out

def bbox_of_ink(img_rgba: Image.Image):
    # Use alpha channel to find non-transparent pixels
    alpha = img_rgba.split()[3]
    return alpha.getbbox()  # returns (left, upper, right, lower) or None

def center_on_canvas(img_rgba: Image.Image, canvas_size: int):
    bbox = bbox_of_ink(img_rgba)
    if bbox is None:
        # fully empty; just return a blank canvas
        return Image.new("RGBA", (canvas_size, canvas_size), (0,0,0,0))

    ink = img_rgba.crop(bbox)
    iw, ih = ink.size

    canvas = Image.new("RGBA", (canvas_size, canvas_size), (0,0,0,0))
    x = (canvas_size - iw) // 2
    y = (canvas_size - ih) // 2
    canvas.alpha_composite(ink, (x, y))
    return canvas

def process_one(path: Path, canvas_size: int, dry_run: bool):
    img = Image.open(path)

    # force RGBA so we can reason about transparency even if source is paletted/RGB
    img_rgba = img.convert("RGBA")

    bg = infer_bg_color(img_rgba)
    img_rgba = make_bg_transparent(img_rgba, bg)

    fixed = center_on_canvas(img_rgba, canvas_size)

    if dry_run:
        return "DRY", path

    # Overwrite in-place (keep as PNG with alpha)
    fixed.save(path, format="PNG")
    return "FIX", path

def main():
    ap = argparse.ArgumentParser(description="Fix Spaceworld front/back summary pics: remove matte bg, center on 64x64 transparent canvas.")
    ap.add_argument("--root", default="graphics/spaceworld/pokemon", help="Root folder containing per-mon sprite dirs.")
    ap.add_argument("--canvas", type=int, default=64, help="Canvas size (default 64).")
    ap.add_argument("--glob", default="**/anim_*.png", help="Glob to select images under root (default **/anim_*.png).")
    ap.add_argument("--apply", action="store_true", help="Actually write changes (otherwise dry-run).")
    args = ap.parse_args()

    root = Path(args.root)
    if not root.exists():
        raise SystemExit(f"ERROR: root not found: {root}")

    paths = sorted(root.glob(args.glob))
    if not paths:
        raise SystemExit(f"ERROR: no files matched {args.glob} under {root}")

    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"Mode: {mode}")
    print(f"Root: {root}")
    print(f"Files: {len(paths)}")
    changed = 0

    for p in paths:
        tag, _ = process_one(p, args.canvas, dry_run=(not args.apply))
        if tag == "FIX":
            changed += 1
        print(f"{tag}: {p}")

    if args.apply:
        print(f"Done. Wrote {changed} files.")
    else:
        print("Dry-run complete. Re-run with --apply to write.")

if __name__ == "__main__":
    main()
