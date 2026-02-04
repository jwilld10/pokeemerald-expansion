#!/usr/bin/env bash
set -euo pipefail

C="src/bw3g_pokemon_pics.c"
if [[ ! -f "$C" ]]; then
  echo "ERROR: missing $C"
  exit 1
fi

TS="$(date +%Y%m%d_%H%M%S)"
BAK="${C}.bak_${TS}"
cp -a "$C" "$BAK"
echo "Backup created: $BAK"

python3 - <<'PY'
import re, sys, os

path = "src/bw3g_pokemon_pics.c"
text = open(path, "r", encoding="utf-8", errors="replace").read()

# Replace BW3G front/back 2bpp.lz paths with smol equivalents.
# front.animated.2bpp.lz -> anim_front.4bpp.smol
# back.2bpp.lz          -> back.4bpp.smol
text2 = text
text2, n_front = re.subn(r'front\.animated\.2bpp\.lz', 'anim_front.4bpp.smol', text2)
text2, n_back  = re.subn(r'back\.2bpp\.lz', 'back.4bpp.smol', text2)

# Some BW3G repos might name front differently; handle a couple common variants safely.
text2, n_front2 = re.subn(r'front\.2bpp\.lz', 'anim_front.4bpp.smol', text2)

if text2 == text:
  print("No changes made (patterns not found).")
  sys.exit(2)

open(path, "w", encoding="utf-8").write(text2)
print(f"Patched {path}")
print(f"Replacements:")
print(f"  front.animated.2bpp.lz -> anim_front.4bpp.smol : {n_front}")
print(f"  front.2bpp.lz          -> anim_front.4bpp.smol : {n_front2}")
print(f"  back.2bpp.lz           -> back.4bpp.smol       : {n_back}")
PY

echo
echo "Post-patch quick counts:"
echo -n "  2bpp.lz refs: "
rg -o 'graphics/bw3g/pokemon/[^"]+\.2bpp\.lz' "$C" | wc -l || true
echo -n "  .smol refs:   "
rg -o 'graphics/bw3g/pokemon/[^"]+\.smol' "$C" | wc -l || true

echo
echo "Now verifying that referenced smol files exist for a sample..."
python3 - <<'PY'
import re, os
c = open("src/bw3g_pokemon_pics.c","r",encoding="utf-8",errors="replace").read()
paths = re.findall(r'"(graphics/bw3g/pokemon/[^"]+\.smol)"', c)
seen=set(); uniq=[]
for p in paths:
    if p not in seen:
        seen.add(p); uniq.append(p)

missing = 0
for p in uniq[:40]:
    ok = os.path.isfile(p)
    print(("[OK]     " if ok else "[MISSING]"), p)
    if not ok:
        missing += 1
print("sample missing count:", missing)
PY

echo
echo "DONE. Next: rebuild (make -j) and test BW3G summary screen."
