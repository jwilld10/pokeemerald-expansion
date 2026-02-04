#!/usr/bin/env bash
set -euo pipefail

echo "== vanilla frontPic candidates (src/data/pokemon/graphics.h etc) =="
# Try to find one obvious vanilla .4bpp.lz reference
rg -n --no-heading 'front.*\.4bpp(\.lz)?' src include | head -n 20 || true
echo

echo "== show first byte of a known vanilla front pic (best effort) =="
VAN="$(rg -o 'graphics/pokemon/[^"]+front[^"]+\.4bpp(\.lz)?' -n src include | head -n 1 | cut -d: -f2- || true)"
echo "vanilla path guess: $VAN"
if [[ -n "$VAN" && -f "$VAN" ]]; then
  python3 - <<PY
p="$VAN"
b=open(p,"rb").read(1)
print("first byte:", b.hex(), "(expect 10 for LZ77)")
PY
else
  echo "could not locate a vanilla front pic file automatically"
fi
echo

echo "== BW3G front pic example =="
BW="graphics/bw3g/pokemon/snivy/front.animated.2bpp.lz"
echo "bw3g path: $BW"
python3 - <<PY
p="$BW"
b=open(p,"rb").read(1)
print("first byte:", b.hex(), "(currently not 10)")
PY
