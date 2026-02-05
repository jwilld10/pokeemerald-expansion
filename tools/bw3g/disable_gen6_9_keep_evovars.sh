#!/usr/bin/env bash
set -euo pipefail

FILE="include/config/species_enabled.h"

if [[ ! -f "$FILE" ]]; then
  echo "ERROR: $FILE not found"
  exit 1
fi

ts="$(date +%Y%m%d_%H%M%S)"
bak="${FILE}.bak_disable_gen6_9_${ts}"
cp -a "$FILE" "$bak"
echo "Backup: $bak"

# Use perl for robust in-place edits (handles whitespace nicely)
perl -0777 -i -pe '
  s/^(#define\s+P_GEN_6_POKEMON\s+).*/$1FALSE \/\/ Generation 6 Pokémon (XY, ORAS)/m;
  s/^(#define\s+P_GEN_7_POKEMON\s+).*/$1FALSE \/\/ Generation 7 Pokémon (SM, USUM, LGPE)/m;
  s/^(#define\s+P_GEN_8_POKEMON\s+).*/$1FALSE \/\/ Generation 8 Pokémon (SwSh, BDSP, LA)/m;
  s/^(#define\s+P_GEN_9_POKEMON\s+).*/$1FALSE \/\/ Generation 9 Pokémon (SV)/m;

  # Ensure these stay enabled for “keepers”
  s/^(#define\s+P_CROSS_GENERATION_EVOS\s+).*/$1TRUE/m;
  s/^(#define\s+P_REGIONAL_FORMS\s+).*/$1TRUE/m;
' "$FILE"

echo "Patched: $FILE"
echo
echo "Now verify the key lines:"
grep -nE "P_GEN_[6-9]_POKEMON|P_CROSS_GENERATION_EVOS|P_REGIONAL_FORMS" "$FILE" || true
echo
echo "NOTE: Changing enabled species can affect dex/save layouts; you may need a fresh save."
