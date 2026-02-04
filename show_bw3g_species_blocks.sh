#!/usr/bin/env bash
set -euo pipefail

F="src/data/pokemon/species_info/bw3g_families.h"

echo "== Showing SPECIES_SKARMORY_BW3G block (with key fields) =="
awk '
  BEGIN{show=0}
  /^\s*\[SPECIES_SKARMORY_BW3G\]/ {show=1}
  show {print}
  show && /^\s*\},/ {exit}
' "$F" || true

echo
echo "== Showing SPECIES_GENESECT_BW3G block (with key fields) =="
awk '
  BEGIN{show=0}
  /^\s*\[SPECIES_GENESECT_BW3G\]/ {show=1}
  show {print}
  show && /^\s*\},/ {exit}
' "$F" || true

echo
echo "== Grep for the exact symbol names used by those blocks in your pics/icons files =="
rg -n --no-heading 'SPECIES_(SKARMORY|GENESECT)_BW3G|gMon(Front|Back)Pic_.*(SKARMORY|GENESECT).*Bw3g|gBw3gMonIcon_.*(SKARMORY|GENESECT)' \
  src/bw3g_pokemon_pics.c src/bw3g_mon_icons.c include/data/pokemon/bw3g_generated/bw3g_pokemon_pics.h \
  || true
