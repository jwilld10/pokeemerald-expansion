#!/usr/bin/env bash
set -euo pipefail
cd ~/decomps/pokeemerald-expansion_clean

OUT="rom_map_snapshot_$(date +%Y%m%d_%H%M%S).out.txt"
echo "Writing $OUT"

echo "== Linked object sizes (map/tileset heavy) ==" > "$OUT"
for p in \
  build/emerald/data/maps.o \
  build/emerald/data/map_events.o \
  build/emerald/src/tilesets.o \
  build/emerald/data/event_scripts.o \
  build/emerald/src/field_specials.o \
  build/emerald/src/scrcmd.o \
  build/emerald/src/wild_encounter.o
do
  if [[ -f "$p" ]]; then
    ls -lh "$p" | tee -a "$OUT"
  fi
done

echo >> "$OUT"
echo "== Raw folder sizes (maps/tilesets) ==" >> "$OUT"
for d in data/maps data/map_events data/tilesets data/layouts graphics/tilesets graphics/field_maps; do
  [[ -e "$d" ]] && du -sh "$d" | tee -a "$OUT"
done

echo >> "$OUT"
echo "== Count of maps (rough) ==" >> "$OUT"
if [[ -d data/maps ]]; then
  find data/maps -type f | wc -l | awk '{print "data/maps files:", $1}' | tee -a "$OUT"
fi
if [[ -d data/layouts ]]; then
  find data/layouts -type f | wc -l | awk '{print "data/layouts files:", $1}' | tee -a "$OUT"
fi

echo >> "$OUT"
echo "DONE. WROTE: $OUT" >> "$OUT"
echo "WROTE: $OUT"
