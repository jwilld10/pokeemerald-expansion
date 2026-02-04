#!/usr/bin/env bash
set -euo pipefail

echo "== Likely u8 truncation sites for species IDs =="
echo

echo "-- u8 variables named species/monSpecies/etc --"
rg -n --no-heading '\bu8\s+(species|monSpecies|pokeSpecies|pkmnSpecies|sSpecies|sp)\b' src include || true
echo

echo "-- casts to u8 around SPECIES_ or species vars --"
rg -n --no-heading '\(\s*u8\s*\)\s*SPECIES_|SPECIES_.*\(\s*u8\s*\)|\(\s*u8\s*\)\s*species' src include || true
echo

echo "-- CreateMon / GiveMon call sites (look for u8 params or casts) --"
rg -n --no-heading '\b(CreateMon|GiveMon|ScriptGiveMon|CreateBoxMon)\s*\(' src || true
echo

echo "-- Common debug/starter menus --"
rg -n --no-heading 'starter|debug.*pokemon|give.*pokemon|add.*pokemon|party.*add' src || true
