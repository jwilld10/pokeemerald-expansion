#!/usr/bin/env bash
set -euo pipefail

CFILE="src/bw3g_pokemon_pics.c"

if [[ ! -f "$CFILE" ]]; then
  echo "ERROR: missing $CFILE"
  exit 1
fi

echo "== Scanning INCBIN paths in $CFILE =="
echo

python3 - <<'PY'
import re, os, sys

cfile = "src/bw3g_pokemon_pics.c"
text = open(cfile, "r", encoding="utf-8", errors="replace").read()

# Grab quoted paths inside INCBIN / INCBIN_U16 / INCBIN_U32 / INCBIN_LZ / etc.
paths = re.findall(r'INCBIN[^()]*\(\s*"([^"]+)"\s*\)', text)
# Some repos use INCBIN("...") without suffix
paths += re.findall(r'\bINCBIN\s*\(\s*"([^"]+)"\s*\)', text)

# Dedup while keeping order
seen = set()
uniq = []
for p in paths:
  if p not in seen:
    seen.add(p); uniq.append(p)

print(f"Found {len(uniq)} unique INCBIN paths.\n")

def lz77_like(fp):
  try:
    with open(fp, "rb") as f:
      b0 = f.read(1)
    return b0 == b"\x10"
  except FileNotFoundError:
    return None

bad = 0
missing = 0
for p in uniq:
  fp = p
  if not os.path.isfile(fp):
    print(f"[MISSING] {p}")
    missing += 1
    continue
  sz = os.path.getsize(fp)
  lz = lz77_like(fp)
  lz_s = "LZ77(0x10)" if lz else "NOT_LZ77"
  print(f"[OK] {p}  size={sz}  {lz_s}")
  if not lz:
    bad += 1

print("\nSummary:")
print(f"  missing: {missing}")
print(f"  not_lz77: {bad}")
PY
