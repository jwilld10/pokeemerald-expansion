#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

ts="$(date +%Y%m%d_%H%M%S)"
echo "== BW3G species truncation fix (timestamp: $ts) =="

# Files we care about most for "debug -> give mon -> party"
TARGETS=(
  "src/debug.c"
  "src/script_pokemon_util.c"
  "src/mystery_event_script.c"
  "src/pokemon.c"
)

echo
echo "== Step 1: Show likely truncation hits (u8 species, casts, & 0xFF, etc.) =="
for f in "${TARGETS[@]}"; do
  if [[ -f "$f" ]]; then
    echo
    echo "---- $f ----"
    rg -n --no-heading -S \
      "(u8|s8)\s+species\b|\b(species)\s*=\s*\(u8\)|\&\s*0xFF\b|\b0xFF\b.*species|\(species\s*&\s*0xFF\)" \
      "$f" || true
  fi
done

echo
echo "== Step 2: Back up files we might patch =="
for f in "${TARGETS[@]}"; do
  if [[ -f "$f" ]]; then
    cp -a "$f" "$f.bak_bw3g_species_u8fix_${ts}"
    echo "Backup: $f.bak_bw3g_species_u8fix_${ts}"
  fi
done

echo
echo "== Step 3: Apply safe patches =="

# (A) If any of these files declare a local u8 species that is used for mon creation/giving,
# change to u16 species. This is the #1 cause of (species % 256) behavior.
# We only change lines that look like "u8 species" or "s8 species" (word boundary).
for f in "${TARGETS[@]}"; do
  [[ -f "$f" ]] || continue
  perl -0777 -pe '
    s/\b(u8|s8)\s+(species)\b/u16 $2/g
  ' -i "$f"
done

# (B) If there are explicit casts to (u8)species, remove the cast.
# This targets patterns like: foo((u8)species, ...)
for f in "${TARGETS[@]}"; do
  [[ -f "$f" ]] || continue
  perl -0777 -pe '
    s/\(\s*u8\s*\)\s*species\b/species/g
  ' -i "$f"
done

# (C) If something masks species down: species &= 0xFF; or species = species & 0xFF;
# comment it out (rare but deadly for BW3G).
for f in "${TARGETS[@]}"; do
  [[ -f "$f" ]] || continue
  perl -0777 -pe '
    s/^(\s*species\s*([&|^]?=)\s*.*0xFF.*;)\s*$/\/\/ BW3G: disabled truncation: $1/mg;
  ' -i "$f"
done

echo
echo "== Step 4: Show post-patch diff summary (only relevant lines) =="
git --no-pager diff -- "${TARGETS[@]}" | sed -n '1,200p' || true

echo
echo "== Step 5: Rebuild =="
make -j

echo
echo "DONE."
echo "If anything went wrong, restore backups like:"
echo "  cp -a src/debug.c.bak_bw3g_species_u8fix_${ts} src/debug.c"
