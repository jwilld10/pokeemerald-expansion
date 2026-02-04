#!/usr/bin/env bash
set -euo pipefail

echo "== Discovering how this repo builds vanilla anim_front/back .smol files =="

# Pick a known vanilla target that exists in-tree.
T1="graphics/pokemon/bulbasaur/anim_front.4bpp.smol"
T2="graphics/pokemon/bulbasaur/back.4bpp.smol"

if [[ ! -f "$T1" || ! -f "$T2" ]]; then
  echo "ERROR: expected vanilla targets not found:"
  echo "  $T1"
  echo "  $T2"
  exit 1
fi

echo
echo "---- make -n $T1 ----"
make -n "$T1" | sed -n '1,120p'

echo
echo "---- make -n $T2 ----"
make -n "$T2" | sed -n '1,120p'

echo
echo "DONE. Paste this output back; it shows the exact toolchain to replicate for BW3G."
