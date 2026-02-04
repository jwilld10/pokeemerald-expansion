#!/bin/sh
set -e

echo "=== Species Count Diagnostic v2 ==="

echo -n "SPECIES_ defines (species.h): "
grep -R "^#define SPECIES_" include/constants/species.h | grep -v "SPECIES_NONE" | wc -l

echo -n "NUM_SPECIES line: "
grep -n "NUM_SPECIES" include/constants/species.h || echo "NOT FOUND"

echo
echo "[Species info entry count]"
if [ -d src/data/pokemon/species_info ]; then
  echo -n ".baseHP occurrences (src/data/pokemon/species_info/*): "
  rg -g'*.h' "\.baseHP\s*=" src/data/pokemon/species_info | wc -l
else
  echo "No src/data/pokemon/species_info directory found."
fi

echo
echo "[Species names presence]"
echo "Files matching *species_names* under src/data and include/data:"
find src/data include/data -type f -name "*species_names*" -printf "%s %p\n" 2>/dev/null | sort -n | head -n 50 || true

echo
echo "[Spaceworld/BW3G presence in species.h]"
echo -n "species.h lines containing 'SPACEWORLD' or 'SW': "
rg -n "SPACEWORLD|_SW" include/constants/species.h | wc -l || true

echo -n "species.h lines containing 'BW3G': "
rg -n "BW3G" include/constants/species.h | wc -l || true
