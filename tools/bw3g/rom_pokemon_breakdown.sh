#!/usr/bin/env bash
set -euo pipefail
cd ~/decomps/pokeemerald-expansion_clean

OUT="rom_pokemon_breakdown_$(date +%Y%m%d_%H%M%S).out.txt"

echo "== Top object files by size (ROM-linked candidates) ==" | tee "$OUT"
find build/emerald -name "*.o" -printf "%s %p\n" \
  | sort -n | tail -n 80 \
  | awk '{printf "%8.1f KB  %s\n", $1/1024, $2}' \
  | tee -a "$OUT"

echo | tee -a "$OUT"
echo "== Focus: pokemon-related objects ==" | tee -a "$OUT"
find build/emerald -name "*.o" -printf "%s %p\n" \
  | awk '$2 ~ /(pokemon|pokedex|species|learnset|icon|graphics\/pokemon|graphics\/spaceworld|bw3g)/ {print}' \
  | sort -n | tail -n 120 \
  | awk '{printf "%8.1f KB  %s\n", $1/1024, $2}' \
  | tee -a "$OUT"

echo | tee -a "$OUT"
echo "== Mapfile: biggest sections mentioning pokemon/graphics ==" | tee -a "$OUT"
if [[ -f pokeemerald.map ]]; then
  rg -n "build/emerald/.*(pokemon|pokedex|species|learnset|graphics/pokemon|graphics/spaceworld|bw3g).*\.o" pokeemerald.map \
    | head -n 200 \
    | tee -a "$OUT" || true
else
  echo "pokeemerald.map not found. Build once to generate it." | tee -a "$OUT"
fi

echo | tee -a "$OUT"
echo "WROTE: $OUT"
