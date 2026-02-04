#!/usr/bin/env bash
set -euo pipefail

BW_G="graphics/bw3g/pokemon/genesect/anim_front.4bpp.smol"
BW_S="graphics/bw3g/pokemon/skarmory/anim_front.4bpp.smol"

VA_C="graphics/pokemon/charizard/anim_front.4bpp.smol"
VA_B="graphics/pokemon/bulbasaur/anim_front.4bpp.smol"

echo "== Sizes =="
ls -l "$BW_G" "$BW_S" "$VA_C" "$VA_B" 2>/dev/null || true
echo

echo "== sha1 (quick identity check) =="
sha1sum "$BW_G" "$BW_S" "$VA_C" "$VA_B" 2>/dev/null || true
echo

echo "== direct comparisons =="
cmp -s "$BW_G" "$VA_C" && echo "Genesect smol == Charizard smol (IDENTICAL)" || echo "Genesect smol != Charizard smol"
cmp -s "$BW_G" "$VA_B" && echo "Genesect smol == Bulbasaur smol (IDENTICAL)" || echo "Genesect smol != Bulbasaur smol"
echo
cmp -s "$BW_S" "$VA_C" && echo "Skarmory smol == Charizard smol (IDENTICAL)" || echo "Skarmory smol != Charizard smol"
