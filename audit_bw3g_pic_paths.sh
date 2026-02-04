#!/usr/bin/env bash
set -euo pipefail

C="src/bw3g_pokemon_pics.c"

echo "== Auditing BW3G pic asset references in $C =="
echo

echo "------------------------------------------------------------"
echo "1) Count references by type"
echo "------------------------------------------------------------"
echo -n "2bpp.lz refs: "
rg -o 'graphics/bw3g/pokemon/[^"]+\.2bpp\.lz' "$C" | wc -l
echo -n ".smol refs:   "
rg -o 'graphics/bw3g/pokemon/[^"]+\.smol' "$C" | wc -l
echo -n ".gbapal refs: "
rg -o 'graphics/bw3g/pokemon/[^"]+\.gbapal' "$C" | wc -l
echo

echo "------------------------------------------------------------"
echo "2) Show first 30 2bpp.lz paths (these should be eliminated)"
echo "------------------------------------------------------------"
rg -n --no-heading 'graphics/bw3g/pokemon/[^"]+\.2bpp\.lz' "$C" | head -n 30 || true
echo

echo "------------------------------------------------------------"
echo "3) Show first 30 smol paths (these are what we want)"
echo "------------------------------------------------------------"
rg -n --no-heading 'graphics/bw3g/pokemon/[^"]+\.smol' "$C" | head -n 30 || true
echo

echo "------------------------------------------------------------"
echo "4) Verify smol files exist on disk for a few samples"
echo "------------------------------------------------------------"
python3 - <<'PY'
import re, os
c = open("src/bw3g_pokemon_pics.c","r",encoding="utf-8",errors="replace").read()
paths = re.findall(r'"(graphics/bw3g/pokemon/[^"]+\.smol)"', c)
seen=set(); uniq=[]
for p in paths:
    if p not in seen:
        seen.add(p); uniq.append(p)

for p in uniq[:25]:
    print("[OK]" if os.path.isfile(p) else "[MISSING]", p)
PY
