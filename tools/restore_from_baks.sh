#!/bin/sh
set -eu

targets="
include/constants/species.h
src/pokemon_icon.c
src/save.c
include/save.h
include/pokemon.h
src/pokemon.c
src/data/pokemon/species_info.h
"

newest_bak() {
  base="$1"
  find "$(dirname "$base")" -maxdepth 1 -type f -name "$(basename "$base").bak_*" -printf "%T@ %p\n" 2>/dev/null \
  | sort -n | tail -n 1 | awk '{print $2}'
}

echo "=== Restoring newest backups for targets ==="
for t in $targets; do
  b="$(newest_bak "$t" || true)"
  if [ -z "${b:-}" ]; then
    echo "SKIP (no backup): $t"
    continue
  fi
  if [ ! -f "$b" ]; then
    echo "SKIP (bak missing?): $t"
    continue
  fi
  mkdir -p "$(dirname "$t")"
  cp -av "$b" "$t"
done

echo
echo "Done. Run: git status --porcelain"
