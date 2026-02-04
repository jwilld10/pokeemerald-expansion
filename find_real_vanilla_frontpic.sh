#!/usr/bin/env bash
set -euo pipefail

echo "== Searching for a NON-BW3G gMonFrontPic_* definition that uses .4bpp.lz =="
echo

# Find a likely vanilla front pic definition NOT in bw3g files
HIT="$(rg -n --no-heading 'gMonFrontPic_[A-Z0-9_]+\[\]\s*=\s*INCBIN.*"\s*graphics/pokemon/.*\.4bpp\.lz"' src \
  | rg -v 'bw3g|BW3G' \
  | head -n 1 || true)"

if [[ -z "$HIT" ]]; then
  echo "Could not find a vanilla gMonFrontPic_* .4bpp.lz definition via that pattern."
  echo "Trying a broader search for .4bpp.lz INCBIN under graphics/pokemon/ ..."
  HIT="$(rg -n --no-heading 'INCBIN.*"graphics/pokemon/.*\.4bpp\.lz"' src include \
    | rg -v 'bw3g|BW3G' \
    | head -n 1 || true)"
fi

if [[ -z "$HIT" ]]; then
  echo "ERROR: still couldn't find a vanilla .4bpp.lz INCBIN reference."
  exit 1
fi

echo "Found line:"
echo "$HIT"
echo

FILE="$(echo "$HIT" | cut -d: -f1)"
LINE="$(echo "$HIT" | cut -d: -f2)"
TEXT="$(sed -n "${LINE}p" "$FILE")"

echo "From file: $FILE (line $LINE)"
echo "Line text:"
echo "$TEXT"
echo

P="$(python3 - <<PY
import re
s = """$TEXT"""
m = re.search(r'"([^"]+)"', s)
print(m.group(1) if m else "")
PY
)"

echo "Path: $P"
if [[ ! -f "$P" ]]; then
  echo "ERROR: file not found: $P"
  exit 1
fi

python3 - <<PY
import os
p="$P"
with open(p,"rb") as f:
    b=f.read(4)
print("first4:", b.hex(), "(expect 10xxxxxx for GBA LZ77)")
print("size:", os.path.getsize(p))
PY
