#!/usr/bin/env bash
set -euo pipefail

echo "== Repo =="; pwd; echo

echo "============================================================"
echo "1) Find where gMonFrontPic_Bulbasaur is defined (non-BW3G)"
echo "============================================================"
rg -n --no-heading 'gMonFrontPic_Bulbasaur' src include data \
  | rg -v 'bw3g|BW3G' \
  | head -n 30 || true
echo

echo "============================================================"
echo "2) Find INCBIN references to graphics/pokemon (non-BW3G)"
echo "============================================================"
rg -n --no-heading 'INCBIN[^"]*"graphics/pokemon/' src include data \
  | rg -v 'bw3g|BW3G' \
  | head -n 50 || true
echo

echo "============================================================"
echo "3) Find any *.lz / *.4bpp.lz files under graphics/pokemon"
echo "============================================================"
find graphics/pokemon -type f \( -name "*.lz" -o -name "*.4bpp.lz" -o -name "*.lz77" \) 2>/dev/null | head -n 50 || true
echo

echo "============================================================"
echo "4) Show header bytes for first 10 compressed-looking pokemon pic files"
echo "============================================================"
python3 - <<'PY'
import os, glob

cands = []
for pat in ["graphics/pokemon/**/*.lz", "graphics/pokemon/**/*.4bpp.lz", "graphics/pokemon/**/*.lz77"]:
    cands += glob.glob(pat, recursive=True)

# Dedup + keep stable order
seen=set(); uniq=[]
for p in cands:
    if p not in seen:
        seen.add(p); uniq.append(p)

print("found:", len(uniq))
for p in uniq[:10]:
    try:
        with open(p,"rb") as f:
            b=f.read(4)
        print(p, "first4=", b.hex(), "size=", os.path.getsize(p))
    except FileNotFoundError:
        print("[MISSING]", p)
PY
echo

echo "============================================================"
echo "DONE - paste output back"
echo "============================================================"
