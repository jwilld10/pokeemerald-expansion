#!/usr/bin/env bash
set -euo pipefail
cd ~/decomps/pokeemerald-expansion_clean

OUT="species_generation_coverage_$(date +%Y%m%d_%H%M%S).out.txt"
echo "Writing $OUT"

echo "== Key sizes from build ==" > "$OUT"
ls -lh build/emerald/src/pokemon.o build/emerald/src/move.o build/emerald/src/item.o 2>/dev/null | tee -a "$OUT" || true

echo >> "$OUT"
echo "== Species headers / include structure (where gens are pulled in) ==" >> "$OUT"
rg -n --no-heading "species_info/|#include \".*species_info|GEN_|kalos|alola|galar|hisui|paldea|gen6|gen7|gen8|gen9" \
  src/data/pokemon/species_info.h src/data/pokemon/species_info/* include/constants/species*.h \
  2>/dev/null | tee -a "$OUT" || true

echo >> "$OUT"
echo "== Rough count of GEN_ constants in species.h ==" >> "$OUT"
if [[ -f include/constants/species.h ]]; then
  rg -n "GEN_[0-9]" include/constants/species.h | wc -l | awk '{print "GEN_ markers in species.h:", $1}' | tee -a "$OUT"
fi

echo >> "$OUT"
echo "== List species_* headers present ==" >> "$OUT"
ls -la include/constants/species*.h 2>/dev/null | tee -a "$OUT" || true

echo >> "$OUT"
echo "DONE. WROTE: $OUT" >> "$OUT"
echo "WROTE: $OUT"
