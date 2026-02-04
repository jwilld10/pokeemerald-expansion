#!/usr/bin/env bash
set -euo pipefail

FILE="src/data/pokemon/species_info/bw3g_families.h"

echo "== Dumping BW3G Species → FrontPic mapping =="
echo

rg -n '\[SPECIES_.*BW3G\]' -n "$FILE" | head -n 40

echo
echo "---- Show mapping blocks for first few BW3G species ----"
echo

python3 - <<'PY'
import re

f = open("src/data/pokemon/species_info/bw3g_families.h","r",encoding="utf8")
data = f.read()

blocks = re.findall(r'\[SPECIES_[A-Z0-9_]+_BW3G\].*?\},', data, re.S)

for b in blocks[:20]:
    species = re.search(r'\[(SPECIES_[A-Z0-9_]+_BW3G)\]', b)
    front = re.search(r'\.frontPic\s*=\s*\(.*?\)\s*(gMonFrontPic_[A-Za-z0-9_]+)', b)
    if species:
        print(species.group(1))
        print("   frontPic:", front.group(1) if front else "MISSING")
        print()
PY
