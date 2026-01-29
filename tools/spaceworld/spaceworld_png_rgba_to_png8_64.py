#!/usr/bin/env python3
import argparse
from pathlib import Path
from PIL import Image

def pad_center_rgba_to_64(img_rgba: Image.Image) -> Image.Image:
    # No scaling. Just center on 64x64.
    if img_rgba.mode != "RGBA":
        img_rgba = img_rgba.convert("RGBA")
    if img_rgba.size == (64, 64):
        return img_rgba
    w, h = img_rgba.size
    out = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    x = (64 - w) // 2
    y = (64 - h) // 2
    out.paste(img_rgba, (x, y))
    return out

def rgba_to_indexed_preserve_colors(img_rgba_64: Image.Image) -> Image.Image:
    # Collect unique visible colors (alpha>0)
    px = img_rgba_64.getdata()
    colors = []
    seen = set()
    for r,g,b,a in px:
        if a == 0:
            continue
        key = (r,g,b)
        if key not in seen:
            seen.add(key)
            colors.append(key)

    # We must fit into 16-color palette: index0 is transparency, so <= 15 visible colors
    if len(colors) > 15:
        raise SystemExit(f"ERROR: uses {len(colors)} visible colors (>15). Refusing to quantize (would change colors).")

    # Build palette: index0 dummy (will be transparent), then sprite colors
    palette = [(0,0,0)] + colors
    # pad palette to 256 entries
    palette += [(0,0,0)] * (256 - len(palette))

    out = Image.new("P", (64, 64), 0)
    flatpal = []
    for r,g,b in palette:
        flatpal.extend([r,g,b])
    out.putpalette(flatpal)

    # Map pixels: transparent -> 0, else exact match to palette
    pal_index = {c:i+1 for i,c in enumerate(colors)}  # visible start at 1
    out_px = []
    for r,g,b,a in px:
        if a == 0:
            out_px.append(0)
        else:
            idx = pal_index.get((r,g,b))
            if idx is None:
                # Shouldn't happen, but keep it strict
                raise SystemExit(f"ERROR: pixel color {(r,g,b)} not in collected palette (unexpected).")
            out_px.append(idx)

    out.putdata(out_px)
    out.info["transparency"] = 0  # tRNS: index 0 transparent
    return out

def process_file(p: Path, apply: bool) -> bool:
    im = Image.open(p)
    if im.mode != "RGBA":
        im = im.convert("RGBA")
    im64 = pad_center_rgba_to_64(im)
    out = rgba_to_indexed_preserve_colors(im64)

    # Detect whether it changed (cheap compare: mode/size/transparency + bytes)
    changed = True
    if p.exists():
        try:
            cur = Image.open(p)
            if cur.mode == out.mode and cur.size == out.size and cur.info.get("transparency") == out.info.get("transparency"):
                # compare raw file bytes
                if p.read_bytes() == _encode_png(out):
                    changed = False
        except Exception:
            pass

    if apply:
        p.write_bytes(_encode_png(out))

    return changed

def _encode_png(img: Image.Image) -> bytes:
    import io
    buf = io.BytesIO()
    # Optimize off to reduce CPU spikes; still fine size-wise.
    img.save(buf, format="PNG", optimize=False)
    return buf.getvalue()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", nargs="?", default="graphics/spaceworld/pokemon", help="Root folder to scan")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--include-female", action="store_true", help="Also process anim_frontf.png")
    ap.add_argument("--exclude", action="append", default=[], help="Substring match to skip (can repeat)")
    args = ap.parse_args()

    root = Path(args.root)
    targets = ["anim_front.png"]
    if args.include_female:
        targets.append("anim_frontf.png")

    files = []
    for name in targets:
        files.extend(root.rglob(name))

    total = 0
    changed = 0
    failed = 0

    for p in sorted(files):
        sp = str(p)
        if any(x in sp for x in args.exclude):
            continue
        total += 1
        try:
            im = Image.open(p)
            mode = im.mode
            size = im.size
            # Only act if not already P 64x64 with transparency
            already_ok = (mode == "P" and size == (64, 64) and im.info.get("transparency") is not None)
            if already_ok:
                print(f"== [skip:ok] {p}")
                continue

            did_change = process_file(p, args.apply)
            tag = "APPLIED" if args.apply else "DRY"
            print(f"{tag}: {p} | from {mode} {size} -> P (64,64) tRNS0")
            if did_change:
                changed += 1
        except SystemExit as e:
            failed += 1
            print(f"ERROR: {p}: {e}")
        except Exception as e:
            failed += 1
            print(f"ERROR: {p}: {e}")

    print(f"Done. processed={total} changed={changed} failed={failed}")

if __name__ == "__main__":
    main()
