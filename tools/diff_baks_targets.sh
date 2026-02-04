#!/bin/sh
set -eu

targets="
include/constants/species.h
src/pokemon_icon.c
src/pokemon.c
src/save.c
include/save.h
include/pokemon.h
src/data/pokemon/species_info.h
include/data/text/species_names_bw3g.inc
"

newest_bak() {
  base="$1"
  # pick newest mtime
  find "$(dirname "$base")" -maxdepth 1 -type f -name "$(basename "$base").bak_*" -printf "%T@ %p\n" 2>/dev/null \
  | sort -n | tail -n 1 | awk '{print $2}'
}

echo "=== Diffstat vs newest backup ==="
for t in $targets; do
  b="$(newest_bak "$t" || true)"
  if [ -z "${b:-}" ]; then
    echo "NO BACKUP: $t"
    continue
  fi
  if [ ! -f "$t" ]; then
    echo "MISSING CURRENT: $t  (bak: $b)"
    continue
  fi
  echo
  echo "--- $t"
  echo "bak: $b"
  diff -u "$b" "$t" | diffstat || echo "(no diff or diffstat missing)"
done
