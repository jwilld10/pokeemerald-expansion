#!/usr/bin/env bash
set -euo pipefail

# Approximates missing .height/.weight for SPACEWORLD by:
#  - resolving each species's PNG front sprite (anim_front.png) from frontPic symbol name
#  - measuring non-transparent bounding box height in pixels
#  - fitting a simple linear regression to known (height, weight)
#  - patching only missing .height/.weight
#
# Requires Pillow:
#   python3 -c "import PIL"  (pip install pillow if missing)

OUT_H="src/data/pokemon/spaceworld_generated/spaceworld_species_info.h"
PNG_ROOT="graphics/spaceworld/pokemon"

[[ -f "$OUT_H" ]] || { echo "ERROR: missing $OUT_H" >&2; exit 1; }
[[ -d "$PNG_ROOT" ]] || { echo "ERROR: missing $PNG_ROOT" >&2; exit 1; }

MIN_H="${MIN_HEIGHT:-1}"
MAX_H="${MAX_HEIGHT:-250}"
MIN_W="${MIN_WEIGHT:-1}"
MAX_W="${MAX_WEIGHT:-9999}"

python3 - "$OUT_H" "$PNG_ROOT" "$MIN_H" "$MAX_H" "$MIN_W" "$MAX_W" <<'PY'
from __future__ import annotations
from pathlib import Path
import math
import re
import sys

try:
    from PIL import Image
except Exception as e:
    print("ERROR: Pillow not available. Install with: pip install pillow", file=sys.stderr)
    raise

OUT_H = Path(sys.argv[1])
PNG_ROOT = Path(sys.argv[2])
MIN_H, MAX_H, MIN_W, MAX_W = map(int, sys.argv[3:])

txt = OUT_H.read_text(encoding="utf-8", errors="ignore")

# --- Parse species blocks ---
key_re = re.compile(r'^\s*\[\s*(SPECIES_[A-Z0-9_]+_SPACEWORLD)\s*\]\s*=\s*\{', re.M)
keys = [(m.start(), m.group(1)) for m in key_re.finditer(txt)]
if not keys:
    print("ERROR: couldn't find any SPECIES_*_SPACEWORLD blocks", file=sys.stderr)
    sys.exit(1)

def slice_block(src: str, start_idx: int) -> tuple[int,int]:
    i = src.find("{", start_idx)
    if i < 0:
        return start_idx, start_idx
    depth = 0
    j = i
    while j < len(src):
        c = src[j]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                end = j + 1
                m = re.match(r'\s*,', src[end:])
                if m:
                    end += m.end()
                return i, end
        j += 1
    return i, len(src)

front_re  = re.compile(r'^\s*\.frontPic\s*=\s*(gSwMonFrontPic_[A-Za-z0-9_]+)\s*,?\s*$', re.M)
height_re = re.compile(r'^\s*\.height\s*=\s*([0-9]+)\s*,?\s*$', re.M)
weight_re = re.compile(r'^\s*\.weight\s*=\s*([0-9]+)\s*,?\s*$', re.M)

def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v

# --- Resolve PNG from frontPic symbol ---
# gSwMonFrontPic_Abra -> "abra" -> graphics/spaceworld/pokemon/abra/anim_front.png
def resolve_front_png(front_sym: str) -> Path | None:
    m = re.match(r'^gSwMonFrontPic_(.+)$', front_sym)
    if not m:
        return None
    name = m.group(1)
    # Folder names in your tree look lowercase (abra)
    folder = name.lower()
    cand = [
        PNG_ROOT / folder / "anim_front.png",
        PNG_ROOT / folder / "front.png",
        PNG_ROOT / folder / "front_pic.png",
        PNG_ROOT / folder / "anim_front.webp",
    ]
    for p in cand:
        if p.exists():
            return p
    return None

def bbox_height_px(png: Path) -> int | None:
    im = Image.open(png).convert("RGBA")
    # getbbox uses alpha too; but if alpha is unused, still okay. We'll build bbox on alpha>0.
    alpha = im.split()[-1]
    bb = alpha.getbbox()
    if not bb:
        return None
    x0, y0, x1, y1 = bb
    return max(1, y1 - y0)

# --- Collect training rows: feature = log(bbox_height_px) ---
train_x = []
train_h = []
train_w = []

targets: list[tuple[str,int,int,str]] = []
missing_hw = 0
no_png = 0

for pos, species in keys:
    b0, b1 = slice_block(txt, pos)
    block = txt[b0:b1]
    fm = front_re.search(block)
    if not fm:
        continue
    front_sym = fm.group(1)

    hm = height_re.search(block)
    wm = weight_re.search(block)
    have_h = hm is not None
    have_w = wm is not None

    png = resolve_front_png(front_sym)
    feat = None
    if png:
        bh = bbox_height_px(png)
        if bh:
            feat = math.log(bh)

    if have_h and have_w and feat is not None:
        train_x.append(feat)
        train_h.append(int(hm.group(1)))
        train_w.append(int(wm.group(1)))
    else:
        if (not have_h) or (not have_w):
            missing_hw += 1
            targets.append((species, b0, b1, front_sym))
            if feat is None:
                no_png += 1

print(f"Total SPACEWORLD blocks: {len(keys)}")
print(f"Missing height/weight blocks: {missing_hw}")
print(f"Training rows (known hw + resolvable PNG): {len(train_x)}")
print(f"Missing blocks with NO usable PNG bbox: {no_png}")

if len(train_x) < 30:
    print("ERROR: too few training rows; resolver still not matching your PNG layout.", file=sys.stderr)
    sys.exit(1)

def linfit(xs, ys):
    n = len(xs)
    sx = sum(xs)
    sy = sum(ys)
    sxx = sum(x*x for x in xs)
    sxy = sum(x*y for x,y in zip(xs,ys))
    den = n*sxx - sx*sx
    if den == 0:
        return 0.0, (sy/n)
    a = (n*sxy - sx*sy) / den
    b = (sy - a*sx) / n
    return a,b

ah,bh = linfit(train_x, train_h)
aw,bw = linfit(train_x, train_w)

out = txt
patched = 0
still_missing = []

for species, b0, b1, front_sym in reversed(targets):
    block = out[b0:b1]
    need_h = height_re.search(block) is None
    need_w = weight_re.search(block) is None
    if not (need_h or need_w):
        continue

    png = resolve_front_png(front_sym)
    if not png:
        still_missing.append(species)
        continue
    bhpx = bbox_height_px(png)
    if not bhpx:
        still_missing.append(species)
        continue

    x = math.log(bhpx)
    pred_h = clamp(int(round(ah*x + bh)), MIN_H, MAX_H)
    pred_w = clamp(int(round(aw*x + bw)), MIN_W, MAX_W)

    insert_lines = []
    if need_h: insert_lines.append(f"    .height = {pred_h},")
    if need_w: insert_lines.append(f"    .weight = {pred_w},")
    insert_blob = "\n" + "\n".join(insert_lines) + "\n"

    m = re.search(r'\n\}\s*,?\s*$', block)
    if not m:
        still_missing.append(species)
        continue
    ins_at = m.start()
    block2 = block[:ins_at] + insert_blob + block[ins_at:]
    out = out[:b0] + block2 + out[b1:]
    patched += 1

OUT_H.write_text(out, encoding="utf-8")
print("----")
print(f"Patched blocks: {patched}")
print(f"Still missing after patch: {len(still_missing)}")
for s in sorted(set(still_missing))[:80]:
    print(s)
print(f"Wrote: {OUT_H}")
PY
