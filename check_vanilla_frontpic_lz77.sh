#!/usr/bin/env bash
set -euo pipefail

echo "== Locate a vanilla gMonFrontPic_ definition and inspect its INCBIN file =="
echo

# Find a definition line that looks like a real mon front pic blob.
HIT="$(rg -n --no-heading 'gMonFrontPic_.*=\s*INCBIN' src | head -n 1 || true)"

if [[ -z "$HIT" ]]; then
  echo "Could not find a gMonFrontPic_* = INCBIN(...) definition in src/"
  echo "Trying broader search..."
  HIT="$(rg -n --no-heading 'gMonFrontPic_' src | head -n 20 || true)"
  echo "$HIT"
  exit 1
fi

echo "Found definition line:"
echo "$HIT"
echo

FILE="$(echo "$HIT" | cut -d: -f1)"
LINE="$(echo "$HIT" | cut -d: -f2)"
echo "From file: $FILE (line $LINE)"
echo

# Extract the quoted path from that definition line
PATH_LINE="$(sed -n "${LINE}p" "$FILE")"
echo "Definition text:"
echo "$PATH_LINE"
echo

P="$(python3 - <<PY
import re
s = """$PATH_LINE"""
m = re.search(r'"([^"]+)"', s)
print(m.group(1) if m else "")
PY
)"

if [[ -z "$P" ]]; then
  echo "ERROR: couldn't extract quoted path from line"
  exit 1
fi

echo "INCBIN path: $P"
if [[ ! -f "$P" ]]; then
  echo "ERROR: file not found: $P"
  exit 1
fi

python3 - <<PY
p="$P"
b=open(p,"rb").read(1)
print("first byte:", b.hex(), "(0x10 means GBA LZ77)")
print("size:", __import__("os").path.getsize(p))
PY
