#!/usr/bin/env bash
set -euo pipefail

DIR="graphics/bw3g/icons"
if [[ ! -d "$DIR" ]]; then
  echo "ERROR: missing dir $DIR"
  exit 1
fi

python3 - <<'PY'
import os, glob
from collections import Counter

paths = sorted(glob.glob("graphics/bw3g/icons/*.4bpp"))
print(f"Found {len(paths)} icon files.\n")

def nibble_hist(data, limit=4096):
  data = data[:limit]
  c = Counter()
  for b in data:
    c[b & 0xF] += 1
    c[(b >> 4) & 0xF] += 1
  total = sum(c.values()) or 1
  top = c.most_common(5)
  return [(n, round(v/total, 3)) for n, v in top]

bad_size = 0
for p in paths:
  sz = os.path.getsize(p)
  ok = (sz == 512 or sz == 1024)
  if not ok:
    bad_size += 1
  with open(p, "rb") as f:
    data = f.read()
  top = nibble_hist(data)
  flag = "OKSIZE" if ok else "BADSZ"
  print(f"{flag}  {os.path.basename(p):28}  size={sz:4}  top_nibbles={top}")

print(f"\nBad-size count: {bad_size}")
PY
