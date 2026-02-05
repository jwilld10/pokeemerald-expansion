#!/usr/bin/env bash
set -euo pipefail
cd ~/decomps/pokeemerald-expansion_clean

OUT="pokemon_o_inputs_report_$(date +%Y%m%d_%H%M%S).out.txt"
echo "Writing $OUT"

echo "== pokemon.o object size ==" > "$OUT"
if [[ -f build/emerald/src/pokemon.o ]]; then
  ls -lh build/emerald/src/pokemon.o | tee -a "$OUT"
fi

echo >> "$OUT"
echo "== Where pokemon.c is compiled from ==" >> "$OUT"
rg -n --no-heading "src/pokemon\.c" -S build/emerald -g'*.d' 2>/dev/null | head -n 40 | tee -a "$OUT" || true

echo >> "$OUT"
echo "== Core includes that likely feed pokemon.o ==" >> "$OUT"
rg -n --no-heading \
  "species_info\.h|level_up_learnsets|pokedex_text|species_names|egg_moves|tmhm_learnsets|evolution|formSpeciesIdTable" \
  src/pokemon.c src/data/pokemon/* include/data/pokemon/* \
  2>/dev/null | tee -a "$OUT" || true

echo >> "$OUT"
echo "== BW3G / Spaceworld includes found in the core data headers ==" >> "$OUT"
rg -n --no-heading "bw3g|spaceworld" \
  src/pokemon.c src/data/pokemon/species_info.h src/data/pokemon/species_info/* include/data/pokemon/* \
  2>/dev/null | tee -a "$OUT" || true

echo >> "$OUT"
echo "== Gen 6-9 related markers (kalos/alola/galar/hisui/paldea) ==" >> "$OUT"
rg -n --no-heading "kalos|alola|galar|hisui|paldea|gen6|gen7|gen8|gen9" \
  src/data/pokemon include/data/pokemon src/pokemon.c \
  2>/dev/null | head -n 400 | tee -a "$OUT" || true

echo >> "$OUT"
echo "DONE." >> "$OUT"
echo "WROTE: $OUT"
