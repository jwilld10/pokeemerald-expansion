#!/usr/bin/env bash
set -euo pipefail

C="src/bw3g_pokemon_pics.c"
if [[ ! -f "$C" ]]; then
  echo "ERROR: missing $C"
  exit 1
fi

echo "== First 10 INCBIN paths found in src/bw3g_pokemon_pics.c =="
python3 - <<'PY'
import re, itertools
text=open("src/bw3g_pokemon_pics.c","r",encoding="utf-8",errors="replace").read()
paths=re.findall(r'INCBIN[^()]*\(\s*"([^"]+)"\s*\)', text)
seen=set(); uniq=[]
for p in paths:
  if p not in seen:
    seen.add(p); uniq.append(p)
for p in uniq[:10]:
  print(p)
print("total:", len(uniq))
PY

echo
echo "== First byte + size of a few BW3G front/back samples =="
python3 - <<'PY'
import re, os
text=open("src/bw3g_pokemon_pics.c","r",encoding="utf-8",errors="replace").read()
paths=re.findall(r'INCBIN[^()]*\(\s*"([^"]+)"\s*\)', text)

# pick a few "front" and "back"
samples=[p for p in paths if "front" in p][:3] + [p for p in paths if "back" in p][:3]
seen=set(); out=[]
for p in samples:
  if p in seen: continue
  seen.add(p); out.append(p)
for p in out[:6]:
  if not os.path.isfile(p):
    print("[MISSING]", p)
    continue
  with open(p,"rb") as f:
    b=f.read(4)
  print(p, " first4=", b.hex(), " size=", os.path.getsize(p))
PY
