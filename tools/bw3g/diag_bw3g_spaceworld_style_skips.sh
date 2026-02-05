#!/usr/bin/env bash
set -euo pipefail

ROOT_REPO="$(pwd)"
BW3G_EXPECTED="${BW3G_PNG_ROOT:-}"

echo "== Repo root =="
echo "$ROOT_REPO"
echo

echo "== What BW3G_PNG_ROOT is set to? =="
if [[ -n "$BW3G_EXPECTED" ]]; then
  echo "BW3G_PNG_ROOT=$BW3G_EXPECTED"
else
  echo "BW3G_PNG_ROOT is NOT set (script probably hardcodes a path)."
fi
echo

echo "== Check common BW3G PNG locations =="
for d in \
  "$ROOT_REPO/graphics/bw3g/pokemon" \
  "$HOME/decomps/gb/BW3G/gfx/pokemon" \
  "$HOME/decomps/gb/BW3G/gfx/pokemon/" \
  ; do
  if [[ -d "$d" ]]; then
    echo "FOUND DIR: $d"
    echo "  sample front.png count: $(find "$d" -maxdepth 2 -name front.png 2>/dev/null | wc -l)"
  else
    echo "missing:  $d"
  fi
done
echo

echo "== Does the size map exist and have content? =="
if [[ -f /tmp/bw3g_sizes.map ]]; then
  echo "FOUND: /tmp/bw3g_sizes.map"
  echo "lines: $(wc -l < /tmp/bw3g_sizes.map)"
  echo "first 10 lines:"
  head -n 10 /tmp/bw3g_sizes.map || true
else
  echo "MISSING: /tmp/bw3g_sizes.map"
fi
echo

echo "== Does bw3g_families.h contain BW3G species entries? =="
FAMS="src/data/pokemon/species_info/bw3g_families.h"
if [[ -f "$FAMS" ]]; then
  echo "FOUND: $FAMS"
  echo "frontPicSize count: $(rg -n '\.frontPicSize\s*=\s*MON_COORDS_SIZE' "$FAMS" | wc -l)"
  echo "backPicSize count:  $(rg -n '\.backPicSize\s*=\s*MON_COORDS_SIZE' "$FAMS" | wc -l)"
else
  echo "MISSING: $FAMS"
fi
echo

echo "== Show 10 BW3G mon folders from common BW3G source dirs =="
for d in "$ROOT_REPO/graphics/bw3g/pokemon" "$HOME/decomps/gb/BW3G/gfx/pokemon"; do
  if [[ -d "$d" ]]; then
    echo "-- $d --"
    ls -1 "$d" | head -n 10
  fi
done
echo

echo "== Try locating a known example (accelgor/front.png) =="
FOUND="$(find "$HOME/decomps/gb/BW3G/gfx/pokemon" -path '*/accelgor/front.png' 2>/dev/null | head -n 1 || true)"
if [[ -n "$FOUND" ]]; then
  echo "FOUND: $FOUND"
else
  echo "NOT FOUND under $HOME/decomps/gb/BW3G/gfx/pokemon"
fi
