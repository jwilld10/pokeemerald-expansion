#!/bin/sh
set -eu

check() {
  TAG="$1"
  FILE="$2"

  echo "Checking core fields for $TAG in $FILE"
  out="$(python3 tools/audit_species_variant_flex.py "$TAG" "$FILE")"
  echo "$out"

  # Core fields we expect to be fully present (0 missing)
  for k in baseHP baseAttack baseDefense baseSpeed baseSpAttack baseSpDefense \
           types catchRate expYield levelUpLearnset categoryName height weight \
           iconSprite iconPalIndex frontPic
  do
    # Match the missing-count line, then ensure it ends with " 0"
    echo "$out" | rg -n "^\s*$k\s+0$" >/dev/null || {
      echo "ERROR: $TAG core field '$k' is missing in one or more entries."
      exit 1
    }
  done

  echo "OK: $TAG core fields all present."
}

check BW3G src/data/pokemon/species_info/bw3g_families.h
echo
check SPACEWORLD src/data/pokemon/spaceworld_generated/spaceworld_species_info.h

echo
echo "All variant core-field checks passed."
