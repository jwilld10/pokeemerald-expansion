#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:-$HOME/decomps/gb/BW3G}"
ROOT="$(realpath "$ROOT")"

echo "ROOT: $ROOT"
echo

echo "== Direct references =="
rg -n --hidden --no-ignore-vcs -S "dex_entries\.asm|PokedexEntry|PokedexEntryBanks" "$ROOT" || true
echo

echo "== Likely dex entry data file(s) =="
find "$ROOT" -type f \( -iname "dex_entries.asm" -o -iname "*dex*entries*.asm" -o -iname "*pokedex*.asm" \) | sort || true
echo

echo "== Show first 80 lines of dex_entries.asm if present =="
if [[ -f "$ROOT/data/pokemon/dex_entries.asm" ]]; then
  sed -n '1,80p' "$ROOT/data/pokemon/dex_entries.asm"
else
  echo "Not found at: $ROOT/data/pokemon/dex_entries.asm"
fi
