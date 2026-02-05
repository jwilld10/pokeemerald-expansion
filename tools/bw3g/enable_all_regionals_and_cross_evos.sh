#!/usr/bin/env bash
set -euo pipefail
cd ~/decomps/pokeemerald-expansion_clean

FILE="include/config/species_enabled.h"
TS="$(date +%Y%m%d_%H%M%S)"
BAK="${FILE}.bak_keep_regionals_cross_${TS}"
cp -a "$FILE" "$BAK"
echo "Backup: $BAK"

# Turn ON global systems for what you want to keep.
# (Leaves P_GEN_6..9_POKEMON alone — you already set those FALSE.)
perl -0777 -i -pe '
  s/^(#define\s+P_CROSS_GENERATION_EVOS\s+).*/$1TRUE/m;
  s/^(#define\s+P_REGIONAL_FORMS\s+).*/$1TRUE/m;

  # Some repos also have per-region toggles; enable if present.
  s/^(#define\s+P_ALOLAN_FORMS\s+).*/$1TRUE/m;
  s/^(#define\s+P_GALARIAN_FORMS\s+).*/$1TRUE/m;
  s/^(#define\s+P_HISUIAN_FORMS\s+).*/$1TRUE/m;
  s/^(#define\s+P_PALDEAN_FORMS\s+).*/$1TRUE/m;
' "$FILE"

echo
echo "Key lines now:"
grep -nE "P_GEN_[6-9]_POKEMON|P_CROSS_GENERATION_EVOS|P_REGIONAL_FORMS|P_(ALOLAN|GALARIAN|HISUIAN|PALDEAN)_FORMS" "$FILE" || true

echo
echo "Rebuild:"
make -j
