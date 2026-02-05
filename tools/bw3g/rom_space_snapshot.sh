#!/usr/bin/env bash
set -euo pipefail
cd ~/decomps/pokeemerald-expansion_clean

echo "== Build memory report (from last link) =="
# If map exists, show the overall ROM usage lines
if [[ -f pokeemerald.map ]]; then
  # many linkers include "Memory region" block; if not present, this prints nothing
  rg -n "Memory region|ROM:" -n pokeemerald.map || true
fi

echo
echo "== Folder sizes (top level) =="
du -sh graphics/* 2>/dev/null | sort -h | tail -n 30 || true

echo
echo "== Pokemon graphics sizes by major group (if present) =="
for d in graphics/pokemon graphics/pokemon_?? graphics/bw3g graphics/spaceworld graphics/icons graphics/pokemon/icon_palettes; do
  [[ -e "$d" ]] && du -sh "$d"
done 2>/dev/null || true

echo
echo "== Largest compiled objects (from build dir, if present) =="
if [[ -d build/emerald ]]; then
  find build/emerald -name "*.o" -printf "%s %p\n" 2>/dev/null | sort -n | tail -n 30 | awk '{printf "%8.1f KB  %s\n", $1/1024, $2}'
fi

echo
echo "DONE."
