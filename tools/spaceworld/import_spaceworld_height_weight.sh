#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   tools/spaceworld/import_spaceworld_height_weight.sh /path/to/GB_REPO_WITH_DEX
#
# Expects the GB repo to contain:
#   data/pokemon/dex_entries.asm
#   data/pokemon/dex_entries/*.asm
#
# Patches:
#   src/data/pokemon/spaceworld_generated/spaceworld_species_info.h
#
# It only inserts .height/.weight if missing, preferring to insert after .categoryName if present.

ROOT="${1:-$HOME/decomps/gb/SPACEWORLD}"
ROOT="$(realpath "$ROOT")"

DEX_MAIN="$ROOT/data/pokemon/dex_entries.asm"
DEX_DIR="$ROOT/data/pokemon/dex_entries"
OUT_H="src/data/pokemon/spaceworld_generated/spaceworld_species_info.h"

[[ -f "$DEX_MAIN" ]] || { echo "ERROR: missing $DEX_MAIN" >&2; exit 1; }
[[ -d "$DEX_DIR"  ]] || { echo "ERROR: missing $DEX_DIR" >&2; exit 1; }
[[ -f "$OUT_H"    ]] || { echo "ERROR: missing $OUT_H" >&2; exit 1; }

python3 - "$ROOT" "$DEX_MAIN" "$DEX_DIR" "$OUT_H" <<'PY'
from pathlib import Path
import re
import sys

root = Path(sys.argv[1])
dex_main = Path(sys.argv[2])
dex_dir  = Path(sys.argv[3])
out_h    = Path(sys.argv[4])

# Parse includes like:
#   AbraPokedexEntry::   INCLUDE "data/pokemon/dex_entries/abra.asm"
inc_re = re.compile(r'^\s*([A-Za-z0-9_]+)PokedexEntry::\s*INCLUDE\s+"([^"]+)"\s*$', re.M)

dex_main_txt = dex_main.read_text(encoding="utf-8", errors="ignore")
includes = inc_re.findall(dex_main_txt)
if not includes:
    raise SystemExit(f"ERROR: no PokedexEntry includes found in {dex_main}")

# Parse each included entry file for:
#   dw 200, 179 ; height, weight
dw_re = re.compile(r'^\s*dw\s+([0-9]+)\s*,\s*([0-9]+)\s*(?:;.*)?$', re.M)

hw = {}  # SPECIES_*_SPACEWORLD -> (height, weight)
missing_files = []
bad_format = []

for mon, rel in includes:
    relp = Path(rel)
    f = (root / relp).resolve()
    if not f.exists():
        # try by basename in dex_dir
        f2 = (dex_dir / relp.name).resolve()
        if f2.exists():
            f = f2
        else:
            missing_files.append(rel)
            continue

    txt = f.read_text(encoding="utf-8", errors="ignore")
    m = dw_re.search(txt)
    if not m:
        bad_format.append(str(f))
        continue

    h = int(m.group(1))
    w = int(m.group(2))
    sym = f"SPECIES_{mon.upper()}_SPACEWORLD"
    hw[sym] = (h, w)

print(f"Parsed height/weight for {len(hw)} entries.")
if missing_files:
    print("WARNING: include files missing on disk (first 20):")
    for x in missing_files[:20]:
        print("  ", x)
if bad_format:
    print("WARNING: entry files missing 'dw height, weight' (first 20):")
    for x in bad_format[:20]:
        print("  ", x)

# Patch target file
src = out_h.read_text(encoding="utf-8", errors="ignore")

start_re = re.compile(r'^\s*\[\s*(SPECIES_[A-Z0-9_]+_SPACEWORLD)\s*\]\s*=\s*$', re.M)
starts = [(m.start(), m.end(), m.group(1)) for m in start_re.finditer(src)]
if not starts:
    raise SystemExit(f"ERROR: no [SPECIES_*_SPACEWORLD] blocks found in {out_h}")

height_re = re.compile(r'^\s*\.height\s*=', re.M)
weight_re = re.compile(r'^\s*\.weight\s*=', re.M)
catline_re = re.compile(r'^(\s*\.categoryName\s*=\s*.*,\s*)$', re.M)
close_re   = re.compile(r'^\s*\},\s*$', re.M)

# Patch in reverse order so indices don't shift
patched = 0
skipped_no_data = 0
already_ok = 0
unpatchable = 0

for idx in range(len(starts)-1, -1, -1):
    s0, e0, sym = starts[idx]
    s1 = starts[idx+1][0] if idx+1 < len(starts) else len(src)
    block = src[e0:s1]

    if sym not in hw:
        skipped_no_data += 1
        continue

    h, w = hw[sym]
    has_h = bool(height_re.search(block))
    has_w = bool(weight_re.search(block))
    if has_h and has_w:
        already_ok += 1
        continue

    ins = ""
    if not has_h:
        ins += f"        .height = {h},\n"
    if not has_w:
        ins += f"        .weight = {w},\n"

    mcat = catline_re.search(block)
    if mcat:
        insert_at = mcat.end()
        block2 = block[:insert_at] + "\n" + ins + block[insert_at:]
    else:
        mclose = close_re.search(block)
        if not mclose:
            unpatchable += 1
            continue
        insert_at = mclose.start()
        block2 = block[:insert_at] + ins + block[insert_at:]

    src = src[:e0] + block2 + src[s1:]
    patched += 1

out_h.write_text(src, encoding="utf-8")

# quick check after patch
txt = out_h.read_text(encoding="utf-8", errors="ignore")
missing_h = 0
missing_w = 0
for m in start_re.finditer(txt):
    sym = m.group(1)
    start = m.end()
    mnext = start_re.search(txt, start)
    end = mnext.start() if mnext else len(txt)
    block = txt[start:end]
    if not height_re.search(block):
        missing_h += 1
    if not weight_re.search(block):
        missing_w += 1

print("----")
print(f"Patched: {patched}")
print(f"Already had both: {already_ok}")
print(f"No dex data found for: {skipped_no_data}")
print(f"Unpatchable blocks (no close brace match): {unpatchable}")
print(f"Still missing .height in: {missing_h}")
print(f"Still missing .weight in: {missing_w}")
print(f"Wrote: {out_h}")
PY

echo
echo "Done. Re-audit:"
echo "  python3 tools/audit_species_variant_flex.py SPACEWORLD src/data/pokemon/spaceworld_generated/spaceworld_species_info.h"
