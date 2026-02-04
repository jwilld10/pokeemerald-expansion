#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   tools/spaceworld/import_spaceworld_height_weight_from_base_stats.sh /path/to/pokegold-spaceworld
#
# Expects:
#   <ROOT>/data/pokemon/base_stats/*.inc
#
# Patches:
#   src/data/pokemon/spaceworld_generated/spaceworld_species_info.h

ROOT="${1:?usage: $0 /path/to/pokegold-spaceworld}"
ROOT="$(realpath "$ROOT")"

BASE_DIR="$ROOT/data/pokemon/base_stats"
OUT_H="src/data/pokemon/spaceworld_generated/spaceworld_species_info.h"

[[ -d "$BASE_DIR" ]] || { echo "ERROR: missing dir: $BASE_DIR" >&2; exit 1; }
[[ -f "$OUT_H"    ]] || { echo "ERROR: missing file: $OUT_H" >&2; exit 1; }

python3 - "$BASE_DIR" "$OUT_H" <<'PY'
from pathlib import Path
import re
import sys

base_dir = Path(sys.argv[1])
out_h = Path(sys.argv[2])

txt = out_h.read_text(encoding="utf-8", errors="ignore")

# Find SPACEWORLD blocks
start_re = re.compile(r'^\s*\[\s*(SPECIES_[A-Z0-9_]+_SPACEWORLD)\s*\]\s*=\s*$', re.M)
close_re = re.compile(r'^\s*\},\s*$', re.M)
height_re = re.compile(r'^\s*\.height\s*=', re.M)
weight_re = re.compile(r'^\s*\.weight\s*=', re.M)

starts = [(m.start(), m.end(), m.group(1)) for m in start_re.finditer(txt)]
blocks = []
missing = []
for i,(s,e,sym) in enumerate(starts):
    end = starts[i+1][0] if i+1 < len(starts) else len(txt)
    block = txt[e:end]
    miss_h = not bool(height_re.search(block))
    miss_w = not bool(weight_re.search(block))
    blocks.append((s,e,end,sym,miss_h,miss_w))
    if miss_h or miss_w:
        missing.append(sym)

missing_set = {sym.replace("SPECIES_","").replace("_SPACEWORLD","") for sym in missing}

print(f"BASE_DIR: {base_dir}")
print(f"Output file: {out_h}")
print(f"Total species blocks: {len(starts)}")
print(f"Missing height/weight at start: {len(missing)}")
print()

# --- Parse base_stats incs ---
# We don't know exact format, so we try a few common patterns.
# Add more patterns here if you inspect a file and see different tokens.

patterns = [
    # "height = 10" / "weight = 95"
    (re.compile(r'^\s*height\s*[:=]\s*([0-9]+)\b', re.M),
     re.compile(r'^\s*weight\s*[:=]\s*([0-9]+)\b', re.M)),
    # ".height = 10" / ".weight = 95"
    (re.compile(r'^\s*\.height\s*=\s*([0-9]+)\b', re.M),
     re.compile(r'^\s*\.weight\s*=\s*([0-9]+)\b', re.M)),
    # "HEIGHT 10" / "WEIGHT 95"
    (re.compile(r'^\s*HEIGHT\s+([0-9]+)\b', re.M),
     re.compile(r'^\s*WEIGHT\s+([0-9]+)\b', re.M)),
    # "db ... ; height" style is harder; try "dw <h>, <w>"
    (re.compile(r'^\s*dw\s+([0-9]+)\s*,\s*([0-9]+)\b', re.M),
     None),
]

def read_hw_from_inc(p: Path):
    t = p.read_text(encoding="utf-8", errors="ignore")
    for hpat, wpat in patterns:
        if wpat is None:
            m = hpat.search(t)
            if m:
                return int(m.group(1)), int(m.group(2))
        else:
            mh = hpat.search(t)
            mw = wpat.search(t)
            if mh and mw:
                return int(mh.group(1)), int(mw.group(1))
    return None

found = {}
for f in sorted(base_dir.glob("*.inc")):
    key = f.stem.upper()  # filename -> MON KEY (e.g., twinz)
    hw = read_hw_from_inc(f)
    if hw:
        found[key] = hw

print(f"Scanned {len(list(base_dir.glob('*.inc')))} .inc files; found {len(found)} with height/weight candidates")
print()

# --- Patch output header ---
patched = 0
still_missing = []

for s,e,end,sym,miss_h,miss_w in reversed(blocks):
    if not (miss_h or miss_w):
        continue
    mon = sym.replace("SPECIES_","").replace("_SPACEWORLD","")
    key = mon.upper()

    if key not in found:
        still_missing.append(sym)
        continue

    h,w = found[key]
    block = txt[e:end]
    mclose = close_re.search(block)
    if not mclose:
        still_missing.append(sym)
        continue

    add = []
    if miss_h:
        add.append(f"        .height = {h},")
    if miss_w:
        add.append(f"        .weight = {w},")
    ins = "\n".join(add) + "\n"

    insert_at = mclose.start()
    block2 = block[:insert_at] + ins + block[insert_at:]
    txt = txt[:e] + block2 + txt[end:]
    patched += 1

out_h.write_text(txt, encoding="utf-8")

print("----")
print(f"Patched blocks: {patched}")
print(f"Still missing after patch: {len(still_missing)}")
for sym in sorted(still_missing):
    print(sym)
print()
print(f"Wrote: {out_h}")
PY
