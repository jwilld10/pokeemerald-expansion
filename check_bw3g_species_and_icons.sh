#!/usr/bin/env bash
set -euo pipefail

echo "== Repo =="
pwd
echo

BW3G_FAM="src/data/pokemon/species_info/bw3g_families.h"
SPECIES_H="include/constants/species.h"
POKE_ICON="src/pokemon_icon.c"

echo "============================================================"
echo "1) Confirm bw3g_families.h exists and show its header"
echo "============================================================"
if [[ ! -f "$BW3G_FAM" ]]; then
  echo "ERROR: Missing $BW3G_FAM"
  exit 1
fi

echo "-- First 120 lines of bw3g_families.h --"
sed -n '1,120p' "$BW3G_FAM"
echo

echo "============================================================"
echo "2) Are BW3G entries designated initializers?"
echo "   (We expect lines like: [SPECIES_SNIVY_BW3G] = { ... })"
echo "============================================================"
echo "-- First 40 BW3G designated-initializer lines --"
rg -n --no-heading '^\s*\[\s*SPECIES_[A-Z0-9_]+_BW3G\s*\]\s*=\s*\{' "$BW3G_FAM" | head -n 40 || true
echo

echo "-- Count of BW3G designated initializers --"
COUNT_DI="$(rg -n '^\s*\[\s*SPECIES_[A-Z0-9_]+_BW3G\s*\]\s*=\s*\{' "$BW3G_FAM" | wc -l || true)"
echo "designated_initializers=$COUNT_DI"
echo

echo "============================================================"
echo "3) Do BW3G entries set baseHP?"
echo "   (If baseHP is missing/0, SanitizeSpeciesId can return SPECIES_NONE)"
echo "============================================================"
echo "-- Show first 60 occurrences of baseHP in bw3g_families.h --"
rg -n --no-heading '\.baseHP\s*=' "$BW3G_FAM" | head -n 60 || true
echo

echo "-- If baseHP is not present, show any base stat fields present --"
if ! rg -q '\.baseHP\s*=' "$BW3G_FAM"; then
  echo "No .baseHP found. Showing any base stats fields:"
  rg -n --no-heading '\.(baseAttack|baseDefense|baseSpeed|baseSpAttack|baseSpDefense)\s*=' "$BW3G_FAM" | head -n 80 || true
  echo
fi

echo "============================================================"
echo "4) BW3G species range defines and GENESIS_MON vs GENESECT"
echo "============================================================"
if [[ -f "$SPECIES_H" ]]; then
  echo "-- species.h: BW3G species lines around SNIVY/GENESECT/GENESIS_MON (if present) --"
  rg -n --no-heading 'SPECIES_.*_BW3G|SNIVY_BW3G|GENESECT_BW3G|GENESIS_MON_BW3G' "$SPECIES_H" || true
else
  echo "WARN: $SPECIES_H not found"
fi
echo

echo "============================================================"
echo "5) pokemon_icon.c: show BW3G range checks + key calls"
echo "============================================================"
if [[ -f "$POKE_ICON" ]]; then
  echo "-- BW3G range checks in pokemon_icon.c --"
  rg -n --no-heading 'SPECIES_SNIVY_BW3G|GENESECT_BW3G|GENESIS_MON_BW3G|IS_BW3G|BW3G' "$POKE_ICON" || true
else
  echo "WARN: $POKE_ICON not found"
fi
echo

echo "============================================================"
echo "DONE. Paste this output back into chat."
echo "============================================================"
