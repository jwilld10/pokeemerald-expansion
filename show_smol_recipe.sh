#!/usr/bin/env bash
set -euo pipefail

T1="graphics/pokemon/bulbasaur/anim_front.4bpp.smol"
T2="graphics/pokemon/bulbasaur/back.4bpp.smol"

echo "== Forcing make to show the recipe (make -nB) =="
echo

echo "---- $T1 ----"
make -nB "$T1" | sed -n '1,200p'
echo

echo "---- $T2 ----"
make -nB "$T2" | sed -n '1,200p'
echo
