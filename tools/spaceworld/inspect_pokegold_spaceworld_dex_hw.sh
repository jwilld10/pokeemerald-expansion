#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:?usage: $0 /path/to/pokegold-spaceworld}"
ROOT="$(realpath "$ROOT")"

DEX="$ROOT/data/pokemon/dex_entries.asm"
[[ -f "$DEX" ]] || { echo "ERROR: missing $DEX" >&2; exit 1; }

echo "ROOT: $ROOT"
echo "DEX:  $DEX"
echo

echo "== Quick head (first 120 lines) =="
sed -n '1,120p' "$DEX" | nl -ba
echo

echo "== Where are the pointer tables? =="
rg -n "PokedexEntryPointers|EntryPointers" "$DEX" | head -n 60 || true
echo

echo "== Look for common dex-entry text markers in this repo =="
rg -n --no-heading -S \
  "(species name|height|weight|@|next |page |dex entry|pokedex entry)" \
  "$DEX" | head -n 120 || true
echo

echo "== Look for any numeric pairs that might be height/weight (dw/dbw patterns) =="
rg -n --no-heading -S \
  "(\bdw\s+[0-9]+\s*,\s*[0-9]+|\bdbw\s+[0-9]+\s*,\s*[0-9]+|\bdw\s+\$[0-9A-Fa-f]+\s*,\s*\$[0-9A-Fa-f]+)" \
  "$DEX" | head -n 120 || true
echo

echo "== Try to find actual entry data blocks (labels that look like entries) =="
rg -n --no-heading -S \
  "^[A-Za-z0-9_]+PokedexEntry::|^[A-Za-z0-9_]+DexEntry::|^[A-Za-z0-9_]+DexEntry:" \
  "$DEX" | head -n 120 || true
echo

echo "== Extract candidate height/weight pairs with nearest preceding label =="
DEX_PATH="$DEX" python3 - <<'PY'
from pathlib import Path
import os, re

dex_path = os.environ["DEX_PATH"]
lines = Path(dex_path).read_text(encoding="utf-8", errors="ignore").splitlines()

label_re = re.compile(r'^([A-Za-z0-9_]+(?:(?:PokedexEntry)|(?:DexEntry))(?:::{0,1})?)')
pair_re  = re.compile(r'\b(dw|dbw)\s+([0-9]+|\$[0-9A-Fa-f]+)\s*,\s*([0-9]+|\$[0-9A-Fa-f]+)')

last_label = None
found = []

for idx, line in enumerate(lines, start=1):
    m = label_re.search(line.strip())
    if m:
        last_label = m.group(1)

    m2 = pair_re.search(line)
    if m2:
        kind, a, b = m2.group(1), m2.group(2), m2.group(3)
        ctx = "\n".join(lines[max(0, idx-3):min(len(lines), idx+2)])
        found.append((idx, last_label, kind, a, b, ctx))

print(f"DEX: {dex_path}")
print(f"Found {len(found)} numeric-pair candidates in dex_entries.asm")
print()

for i, (lin, label, kind, a, b, ctx) in enumerate(found[:60], start=1):
    print(f"[{i}] line {lin} | label={label} | {kind} {a},{b}")
    print(ctx)
    print("----")

if len(found) > 60:
    print(f"(showing first 60 of {len(found)})")
PY

