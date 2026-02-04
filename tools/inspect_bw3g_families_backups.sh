#!/bin/sh
set -eu

DIR="src/data/pokemon/species_info"
PAT="$DIR/bw3g_families.h*"

echo "=== Listing BW3G families files (size/lines) ==="
for f in $PAT; do
  [ -f "$f" ] || continue
  bytes=$(wc -c < "$f" | tr -d ' ')
  lines=$(wc -l < "$f" | tr -d ' ')
  echo "$bytes bytes | $lines lines | $f"
done | sort -n

echo
echo "=== For each file: what patterns exist? ==="
for f in $PAT; do
  [ -f "$f" ] || continue
  echo
  echo "--- $f ---"
  echo -n "contains '_BW3G' tokens: "
  rg -o '[_A-Z0-9]+_BW3G' "$f" 2>/dev/null | wc -l || echo 0

  echo -n "contains '[SPECIES_*_BW3G] = {' blocks: "
  rg -n '\[\s*SPECIES_[A-Z0-9_]+_BW3G\s*\]\s*=\s*\{' "$f" >/dev/null 2>&1 && echo YES || echo NO

  echo -n "contains '.baseHP' fields: "
  rg -n '\.baseHP\s*=' "$f" >/dev/null 2>&1 && echo YES || echo NO

  echo -n "contains 'SPECIES_' defines: "
  rg -n '^#define\s+SPECIES_' "$f" >/dev/null 2>&1 && echo YES || echo NO

  echo -n "contains macro-style 'FAMILY'/'SPECIES_INFO'/'BEGIN' hints: "
  rg -n 'FAMILY\(|SPECIES_INFO|BEGIN|END|DEFINE|ENTRY\(' "$f" >/dev/null 2>&1 && echo YES || echo NO

  echo "first 5 non-empty lines:"
  rg -n '.+' "$f" | head -n 5
done
