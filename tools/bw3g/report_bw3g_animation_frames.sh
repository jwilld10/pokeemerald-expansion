#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
BW3G_PNG_ROOT="${BW3G_PNG_ROOT:-/home/jwilld10/decomps/gb/BW3G/gfx/pokemon}"
FAM_H="$ROOT/src/data/pokemon/species_info/bw3g_families.h"
OUT="bw3g_animation_frames_report.out.txt"

python3 - <<'PY' "$BW3G_PNG_ROOT" "$FAM_H" "$OUT"
import re, sys
from pathlib import Path

png_root = Path(sys.argv[1])
fam_h = Path(sys.argv[2])
out_path = Path(sys.argv[3])

try:
    from PIL import Image
except Exception as e:
    print("ERROR: Python Pillow (PIL) not available. Install: sudo apt-get install python3-pil", file=sys.stderr)
    raise

def parse_sizes(fam_text: str):
    # mon(lower) -> (fw, fh, bw, bh)
    sizes = {}
    cur = None
    fw = fh = bw = bh = None

    sp_re = re.compile(r"\[\s*SPECIES_([A-Z0-9_]+)_BW3G\s*\]")
    f_re  = re.compile(r"\.frontPicSize\s*=\s*MON_COORDS_SIZE\(\s*(\d+)\s*,\s*(\d+)\s*\)")
    b_re  = re.compile(r"\.backPicSize\s*=\s*MON_COORDS_SIZE\(\s*(\d+)\s*,\s*(\d+)\s*\)")

    def commit():
        nonlocal cur, fw, fh, bw, bh
        if cur and fw and fh and bw and bh:
            sizes[cur.lower()] = (fw, fh, bw, bh)
        cur = None
        fw = fh = bw = bh = None

    for line in fam_text.splitlines():
        m = sp_re.search(line)
        if m:
            commit()
            cur = m.group(1)
            continue
        m = f_re.search(line)
        if m:
            fw, fh = int(m.group(1)), int(m.group(2))
            continue
        m = b_re.search(line)
        if m:
            bw, bh = int(m.group(1)), int(m.group(2))
            continue
        if cur and line.strip().startswith("},"):
            commit()

    commit()
    return sizes

def analyze_sheet(img_w, img_h, fw, fh):
    """
    Returns: (frames, mode, grid_w, grid_h)
    mode: exact | vstrip | hstrip | sheet | unknown
    """
    if fw <= 0 or fh <= 0:
        return (None, "nosize", None, None)

    if (img_w, img_h) == (fw, fh):
        return (1, "exact", 1, 1)

    # vertical strip
    if img_w == fw and img_h % fh == 0:
        return (img_h // fh, "vstrip", 1, img_h // fh)

    # horizontal strip
    if img_h == fh and img_w % fw == 0:
        return (img_w // fw, "hstrip", img_w // fw, 1)

    # sheet (grid)
    if img_w % fw == 0 and img_h % fh == 0:
        gw = img_w // fw
        gh = img_h // fh
        return (gw * gh, "sheet", gw, gh)

    return (None, "unknown", None, None)

fam_text = fam_h.read_text(encoding="utf-8", errors="ignore")
sizes = parse_sizes(fam_text)

lines = []
lines.append("== BW3G animation frame report ==")
lines.append(f"PNG root: {png_root}")
lines.append(f"Sizes from: {fam_h}")
lines.append("")
lines.append("Format:")
lines.append("mon | front: WxH vs frame fw x fh => frames (mode grid) | back: WxH vs frame bw x bh => frames (mode grid)")
lines.append("")

missing_png = 0
missing_size = 0
unknown = 0
multi_front = 0
multi_back = 0
total = 0

if not png_root.exists():
    raise SystemExit(f"ERROR: BW3G_PNG_ROOT does not exist: {png_root}")

for mon_dir in sorted([p for p in png_root.iterdir() if p.is_dir()]):
    mon = mon_dir.name.lower()
    total += 1

    if mon not in sizes:
        missing_size += 1
        continue

    fw, fh, bw, bh = sizes[mon]
    fp = mon_dir / "front.png"
    bp = mon_dir / "back.png"
    if not fp.exists() or not bp.exists():
        missing_png += 1
        continue

    with Image.open(fp) as im:
        fW, fH = im.size
    with Image.open(bp) as im:
        bW, bH = im.size

    f_frames, f_mode, f_gw, f_gh = analyze_sheet(fW, fH, fw, fh)
    b_frames, b_mode, b_gw, b_gh = analyze_sheet(bW, bH, bw, bh)

    if f_frames is None or b_frames is None:
        unknown += 1

    if f_frames and f_frames > 1:
        multi_front += 1
    if b_frames and b_frames > 1:
        multi_back += 1

    def fmt(frames, mode, gw, gh):
        if frames is None:
            return f"? ({mode})"
        if mode == "sheet":
            return f"{frames} ({mode} {gw}x{gh})"
        if mode in ("vstrip", "hstrip"):
            return f"{frames} ({mode})"
        return f"{frames} ({mode})"

    lines.append(
        f"{mon} | "
        f"front {fW}x{fH} vs {fw}x{fh} => {fmt(f_frames, f_mode, f_gw, f_gh)} | "
        f"back {bW}x{bH} vs {bw}x{bh} => {fmt(b_frames, b_mode, b_gw, b_gh)}"
    )

out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

print(f"WROTE: {out_path}")
print("")
print("Summary:")
print(f"  mons_total_dirs           = {total}")
print(f"  missing_size_in_families  = {missing_size}")
print(f"  missing_front_or_back_png = {missing_png}")
print(f"  unknown_layout            = {unknown}")
print(f"  multi_frame_front         = {multi_front}")
print(f"  multi_frame_back          = {multi_back}")
print("")
print("Top 40 lines:")
print("\n".join(lines[:40]))
PY
