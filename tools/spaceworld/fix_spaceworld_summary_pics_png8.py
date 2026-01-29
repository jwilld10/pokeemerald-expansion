#!/usr/bin/env python3
import argparse
from pathlib import Path
from PIL import Image
from collections import Counter

def infer_bg_color(img_rgba: Image.Image):
    px = img_rgba.load()
    w, h = img_rgba.size
    samples = [
        px[0,0], px[w-1,0], px[0,h-1], px[w-1,h-1],
        px[w//2, 0], px[w//2, h-1], px[0, h//2], px[w-1, h//2],
    ]
    if any(s[3] == 0 for s in samples):
        return None
    return Counter(samples).most_common(1)[0][0]

def make_bg_transparent(img_rgba: Image.Image, bg_rgba):
    if bg_rgba is None:
        return img_rgba
    br, bg, bb, ba = bg_rgba
    data = img_rgba.getdata()
    new = []
    for (r,g,b,a) in data:
        if (r,g,b,a) == (br,bg,bb,ba):
            new.append((0,0,0,0))
        else:
            new.append((r,g,b,a))
    out = Image.new("RGBA", img_rgba.size)
    out.putdata(new)
    return out

def bbox_of_ink(img_rgba: Image.Image):
    alpha = img_rgba.split()[3]
    return alpha.getbbox()

def center_on_canvas(img_rgba: Image.Image, canvas_size: int):
    bbox = bbox_of_ink(img_rgba)
    if bbox is None:
        return Image.new("RGBA", (canvas_size, canvas_size), (0,0,0,0))
    ink = img_rgba.crop(bbox)
    iw, ih = ink.size
    canvas = Image.new("RGBA", (canvas_size, canvas_size), (0,0,0,0))
    x = (canvas_size - iw) // 2
    y = (canvas_size - ih) // 2
    canvas.alpha_composite(ink, (x, y))
    return canvas

def rgba_to_png8_16_with_transparency(img_rgba: Image.Image) -> Image.Image:
    """
    Convert RGBA to paletted PNG (mode P) with <=16 colors.
    Ensure transparency is palette index 0.
    """
    # Create an RGB image for quantization; keep alpha mask separately
    alpha = img_rgba.split()[3]
    rgb = img_rgba.convert("RGB")

    # Quantize to <=15 visible colors (we will reserve index 0 for transparent)
    # Then we'll build a new palette where index 0 is transparent.
    q = rgb.quantize(colors=15, method=Image.MEDIANCUT)

    # Convert back to RGB so we can insert a transparent color slot cleanly
    q_rgb = q.convert("RGB")

    # Build a 16-color palette image where palette[0] is transparent color (0,0,0)
    pal_img = Image.new("P", (1, 1))
    palette = [0,0,0]  # index 0 reserved for transparency
    # Get palette from quantized image (up to 256*3 list)
    q_pal = q.getpalette() or []
    # Extract first 15 colors from q palette
    # q palette is 256 entries; we want first 15
    for i in range(15):
        base = i * 3
        if base + 2 < len(q_pal):
            palette.extend(q_pal[base:base+3])
        else:
            palette.extend([0,0,0])
    # Pad to 256 colors (required by PNG palette chunk)
    palette.extend([0,0,0] * (256 - 16))
    pal_img.putpalette(palette)

    # Now map pixels: visible pixels use indices 1..15, transparent pixels use 0
    # We'll re-quantize q_rgb to our fixed palette image
    mapped = q_rgb.quantize(palette=pal_img, dither=Image.Dither.NONE)

    # Apply transparency mask: where alpha == 0 set index to 0
    mapped_data = list(mapped.getdata())
    alpha_data = list(alpha.getdata())
    for i, a in enumerate(alpha_data):
        if a == 0:
            mapped_data[i] = 0
        else:
            # ensure visible indices are not 0
            if mapped_data[i] == 0:
                mapped_data[i] = 1
    out = Image.new("P", mapped.size)
    out.putpalette(palette)
    out.putdata(mapped_data)

    return out

def process_one(path: Path, canvas_size: int, dry_run: bool):
    img = Image.open(path).convert("RGBA")
    bg = infer_bg_color(img)
    img = make_bg_transparent(img, bg)
    img = center_on_canvas(img, canvas_size)
    img_p = rgba_to_png8_16_with_transparency(img)

    if dry_run:
        return "DRY", path
    # Save as paletted PNG with transparency index 0
    img_p.save(path, format="PNG", transparency=0, optimize=False)
    return "FIX", path

def main():
    ap = argparse.ArgumentParser(description="Fix Spaceworld pics: remove matte bg, center on 64x64, output PNG8 paletted (<=16 colors) for gbagfx.")
    ap.add_argument("--root", default="graphics/spaceworld/pokemon", help="Root folder containing per-mon sprite dirs.")
    ap.add_argument("--canvas", type=int, default=64, help="Canvas size (default 64).")
    ap.add_argument("--glob", default="**/anim_*.png", help="Glob to select images under root.")
    ap.add_argument("--apply", action="store_true", help="Write changes (otherwise dry-run).")
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

    for p in paths:
        tag, _ = process_one(p, args.canvas, dry_run=(not args.apply))
        print(f"{tag}: {p}")

    if args.apply:
        print("Done.")
    else:
        print("Dry-run complete. Re-run with --apply to write.")

if __name__ == "__main__":
    main()
