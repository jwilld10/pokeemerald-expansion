#!/usr/bin/env bash
set -euo pipefail

echo "== Repo =="
pwd
echo

FILE="src/pokemon.c"

if [[ ! -f "$FILE" ]]; then
  echo "ERROR: $FILE not found"
  exit 1
fi

echo "============================================================"
echo "1) Location of IsSpeciesEnabled + SanitizeSpeciesId in src/pokemon.c"
echo "============================================================"
rg -n --no-heading "u16 SanitizeSpeciesId|bool32 IsSpeciesEnabled" "$FILE" || true
echo

echo "============================================================"
echo "2) Extract IsSpeciesEnabled() function body"
echo "============================================================"
awk '
  BEGIN{found=0; depth=0;}
  {
    if (!found && $0 ~ /^[[:space:]]*bool32[[:space:]]+IsSpeciesEnabled[[:space:]]*\(/) { found=1 }
    if (found) {
      print
      n=gsub(/{/,"{"); depth+=n
      n=gsub(/}/,"}"); depth-=n
      if (depth<=0 && $0 ~ /}/) { exit }
    }
  }
' "$FILE" || true
echo

echo "============================================================"
echo "3) Show nearby config usage / tables referenced by IsSpeciesEnabled"
echo "   (prints ~120 lines after the function signature)"
echo "============================================================"
LINE="$(rg -n "^[[:space:]]*bool32[[:space:]]+IsSpeciesEnabled[[:space:]]*\\(" "$FILE" | head -n1 | cut -d: -f1 || true)"
if [[ -n "${LINE:-}" ]]; then
  START=$((LINE-20))
  [[ $START -lt 1 ]] && START=1
  END=$((LINE+140))
  sed -n "${START},${END}p" "$FILE"
else
  echo "Could not find IsSpeciesEnabled() definition line."
fi
echo

echo "============================================================"
echo "4) Show config/species_enabled.h header + any BW3G-related lines"
echo "============================================================"
CFG="include/config/species_enabled.h"
if [[ -f "$CFG" ]]; then
  echo "-- header (first 80 lines) --"
  sed -n '1,80p' "$CFG"
  echo

  echo "-- any occurrences of BW3G or species_bw3g or GENESIS_MON in config --"
  rg -n --no-heading "BW3G|bw3g|species_bw3g|GENESIS_MON|GENESECT|SNIVY" "$CFG" || true
  echo
else
  echo "WARN: $CFG not found"
fi

echo "============================================================"
echo "DONE - paste output back"
echo "============================================================"
