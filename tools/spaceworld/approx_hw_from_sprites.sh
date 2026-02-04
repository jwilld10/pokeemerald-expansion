#!/usr/bin/env bash
set -euo pipefail

# Approximates missing .height/.weight in:
#   src/data/pokemon/spaceworld_generated/spaceworld_species_info.h
#
# using file-size regression on the frontPic INCBIN asset (often .smol).
#
# It:
#  1) parses species blocks and collects known (height, weight, frontPic symbol)
#  2) resolves symbol -> asset path by scanning src/data/graphics/spaceworld_pokemon_gfx.c
#  3) trains 1D linear regression on log(file_size) to predict height/weight
#  4) patches missing .height/.weight only
#
# Usage:
#   tools/spaceworld/approx_hw_from_sprites.sh
#
# Optional tuning:
#   MIN_HEIGHT=1 MAX_HEIGHT=250
#   MIN_WEIGHT=1 MAX_WEIGHT=9999

OUT_H="src/data/pokemon/spaceworld_generated/spaceworld_species_info.h"
GFX_C="src/data/graphics/spaceworld_pokemon_gfx.c"

[[ -f "$OUT_H" ]] || { echo "ERROR: missing $OUT_H" >&2; exit 1; }
[[ -f "$GFX_C" ]] || { echo "ERROR: missing $GFX_C" >&2; exit 1; }

MIN_H="${MIN_HEIGHT:-1}"
MAX_H="${MAX_HEIGHT:-250}"
MIN_W="${MIN_WEIGHT:-1}"
MAX_W="${MAX_WEIGHT:-9999}"

python3 - "$OUT_H" "$GFX_C" "$MIN_H" "$MAX_H" "$MIN_W" "$MAX_W" <<'PY'
from __future__ import annotations
from pathlib import Path
import math
import re
import sys

OUT_H = Path(sys.argv[1])
GFX_C = Path(sys.argv[2])
MIN_H, MAX_H, MIN_W, MAX_W = map(int, sys.argv[3:])

txt = OUT_H.read_text(encoding="utf-8", errors="ignore")
gfx = GFX_C.read_text(encoding="utf-8", errors="ignore")

# --- Resolve gSwMonFrontPic_X -> INCBIN path ---
# Example:
# const u32 gSwMonFrontPic_Abra[] = INCBIN_U32("graphics/spaceworld/pokemon/abra/anim_front.4bpp.smol");
sym_to_path: dict[str, Path] = {}
for m in re.finditer(
    r'^\s*const\s+u32\s+(gSwMonFrontPic_[A-Za-z0-9_]+)\s*\[\]\s*=\s*INCBIN_U32\("([^"]+)"\)\s*;',
    gfx,
    flags=re.M,
):
    sym = m.group(1)
    p = Path(m.group(2))
    # resolve relative to repo root
    if not p.exists():
        p = (GFX_C.parent.parent.parent / p).resolve()  # src/data/graphics -> repo root-ish then join
        # That parent math can be brittle; fallback: just try relative to cwd.
        if not p.exists():
            p = Path(m.group(2)).resolve()
    sym_to_path[sym] = p

# --- Parse species blocks: [SPECIES_X] = { ... } ---
key_re = re.compile(r'^\s*\[\s*(SPECIES_[A-Z0-9_]+_SPACEWORLD)\s*\]\s*=\s*\{', re.M)
keys = [(m.start(), m.group(1)) for m in key_re.finditer(txt)]
if not keys:
    print("ERROR: couldn't find any SPECIES_*_SPACEWORLD blocks", file=sys.stderr)
    sys.exit(1)

# For slicing blocks, find matching closing "}," at same indent-ish:
# We'll do a simple brace counter starting from the opening "{"
def slice_block(start_idx: int) -> tuple[int,int]:
    i = txt.find("{", start_idx)
    if i < 0:
        return start_idx, start_idx
    depth = 0
    j = i
    while j < len(txt):
        c = txt[j]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                # include following "}," if present
                end = j + 1
                m = re.match(r'\s*,', txt[end:])
                if m:
                    end += m.end()
                return i, end
        j += 1
    return i, len(txt)

front_re  = re.compile(r'^\s*\.frontPic\s*=\s*(gSwMonFrontPic_[A-Za-z0-9_]+)\s*,?\s*$', re.M)
height_re = re.compile(r'^\s*\.height\s*=\s*([0-9]+)\s*,?\s*$', re.M)
weight_re = re.compile(r'^\s*\.weight\s*=\s*([0-9]+)\s*,?\s*$', re.M)

# Collect training rows: (log(size), height, weight)
train_x = []
train_h = []
train_w = []

# Collect patch targets: species symbol -> (block range, frontSym)
targets: list[tuple[str, int, int, str]] = []

missing_hw = 0
unresolvable = 0

for idx,(pos,species) in enumerate(keys):
    b0, b1 = slice_block(pos)
    block = txt[b0:b1]

    fm = front_re.search(block)
    if not fm:
        continue
    front_sym = fm.group(1)

    hm = height_re.search(block)
    wm = weight_re.search(block)

    have_h = hm is not None
    have_w = wm is not None

    # resolve asset path and size if possible
    asset = sym_to_path.get(front_sym)
    size = None
    if asset and asset.exists():
        try:
            size = asset.stat().st_size
        except OSError:
            size = None

    if have_h and have_w and size and size > 0:
        x = math.log(size)
        train_x.append(x)
        train_h.append(int(hm.group(1)))
        train_w.append(int(wm.group(1)))
    else:
        if (not have_h) or (not have_w):
            missing_hw += 1
            targets.append((species, b0, b1, front_sym))
            if not (asset and asset.exists() and size and size > 0):
                unresolvable += 1

print(f"Total SPACEWORLD blocks: {len(keys)}")
print(f"Missing height/weight blocks: {missing_hw}")
print(f"Training rows (known hw + resolvable asset): {len(train_x)}")
print(f"Missing blocks with NO resolvable asset: {unresolvable}")

if len(train_x) < 30:
    print("ERROR: too few training rows; can't fit a useful regression.", file=sys.stderr)
    sys.exit(1)

# Simple linear regression y = a*x + b
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

def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v

patched = 0
still_missing = []

out = txt

# Patch from back to front so indices stay valid
for species, b0, b1, front_sym in reversed(targets):
    block = out[b0:b1]

    hm = height_re.search(block)
    wm = weight_re.search(block)
    need_h = hm is None
    need_w = wm is None
    if not (need_h or need_w):
        continue

    asset = sym_to_path.get(front_sym)
    if not (asset and asset.exists()):
        still_missing.append(species)
        continue
    try:
        size = asset.stat().st_size
    except OSError:
        still_missing.append(species)
        continue
    if size <= 0:
        still_missing.append(species)
        continue

    x = math.log(size)
    pred_h = int(round(ah*x + bh))
    pred_w = int(round(aw*x + bw))
    pred_h = clamp(pred_h, MIN_H, MAX_H)
    pred_w = clamp(pred_w, MIN_W, MAX_W)

    # Insert .height/.weight near other dex-ish fields; simplest: append just before closing brace.
    insert_lines = []
    if need_h:
        insert_lines.append(f"    .height = {pred_h},")
    if need_w:
        insert_lines.append(f"    .weight = {pred_w},")
    insert_blob = "\n" + "\n".join(insert_lines) + "\n"

    # Put it before the final "\n},"
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
for s in sorted(set(still_missing))[:50]:
    print(s)
print(f"Wrote: {OUT_H}")
PY
