#!/usr/bin/env bash
set -euo pipefail

echo "== Repo =="
pwd
echo

echo "============================================================"
echo "1) Find IsSpeciesEnabled and SanitizeSpeciesId"
echo "============================================================"
rg -n --no-heading "IsSpeciesEnabled\s*\(|SanitizeSpeciesId\s*\(" src include || true
echo

echo "============================================================"
echo "2) Dump IsSpeciesEnabled definition (best effort)"
echo "============================================================"
HITS="$(rg -n "^\s*(static\s+)?(bool8|bool32|u8|u16|int)\s+IsSpeciesEnabled\s*\(" src include || true)"
echo "$HITS"
echo

if [[ -n "$HITS" ]]; then
  FILE="$(echo "$HITS" | head -n1 | cut -d: -f1)"
  echo "-- Extracting IsSpeciesEnabled from $FILE --"
  awk '
    BEGIN{found=0; depth=0;}
    {
      if (!found && $0 ~ /IsSpeciesEnabled[[:space:]]*\(/) { found=1 }
      if (found) {
        print
        n=gsub(/{/,"{"); depth+=n
        n=gsub(/}/,"}"); depth-=n
        if (depth<=0 && $0 ~ /}/) { exit }
      }
    }
  ' "$FILE" || true
  echo
fi

echo "============================================================"
echo "3) Look for species enabled tables/flags"
echo "============================================================"
rg -n --no-heading "gSpeciesEnabled|SpeciesEnabled|SPECIES_ENABLED|species_enabled|ENABLE_SPECIES" src include || true
echo

echo "============================================================"
echo "4) Check whether BW3G species appear in any enable lists"
echo "============================================================"
rg -n --no-heading "_BW3G" include src | head -n 200 || true
echo

echo "============================================================"
echo "5) Confirm NUM_SPECIES and where it's defined"
echo "============================================================"
rg -n --no-heading "NUM_SPECIES\b|SPECIES_EGG\b" include/constants/species.h include || true
echo

echo "============================================================"
echo "DONE - paste output back"
echo "============================================================"
