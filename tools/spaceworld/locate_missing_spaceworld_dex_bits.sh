#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:?usage: $0 /path/to/repo}"
ROOT="$(realpath "$ROOT")"

missing=(
  BELLRUN BELMITT BOMSHEAL CORASUN CRUIZE ELEBABE GELANIA GUPGOLD KURSTRAW METTO
  MR_MIME NYANYA PANGSHI PARAMITE PETAMOLE PETICORN PRAXE PUDDIPUP TANGTRIP
  TRIPSTAR TWINZ WARWOLF
)

echo "ROOT: $ROOT"
echo

echo "== filename hits =="
for m in "${missing[@]}"; do
  hits=$(find "$ROOT" -type f -iname "*$(echo "$m" | tr '[:upper:]' '[:lower:]')*" 2>/dev/null | head -n 5 || true)
  if [[ -n "$hits" ]]; then
    echo "-- $m"
    echo "$hits"
  fi
done
echo

echo "== label hits (PokedexEntry) =="
for m in "${missing[@]}"; do
  rg -n --hidden --no-ignore-vcs -S "^\s*${m}[A-Za-z0-9_]*PokedexEntry::" "$ROOT" 2>/dev/null | head -n 3 || true
done
