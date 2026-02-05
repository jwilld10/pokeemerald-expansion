#!/usr/bin/env bash
set -euo pipefail
cd ~/decomps/pokeemerald-expansion_clean

F="src/pokemon.c"
TS="$(date +%Y%m%d_%H%M%S)"
BAK="${F}.bak_formtable_${TS}"
cp -a "$F" "$BAK"
echo "Backup created: $BAK"

python3 - <<'PY'
import re, sys

path = "src/pokemon.c"
s = open(path, "r", encoding="utf-8", errors="replace").read()

# Find the GetSpeciesFormTable function block.
m = re.search(r'(const\s+u16\s*\*\s*GetSpeciesFormTable\s*\(\s*u16\s+species\s*\)\s*\{.*?\n\})', s, flags=re.S)
if not m:
    # Some trees have "u16 *GetSpeciesFormTable" typo; handle that too
    m = re.search(r'(u16\s*\*\s*GetSpeciesFormTable\s*\(\s*u16\s+species\s*\)\s*\{.*?\n\})', s, flags=re.S)
if not m:
    print("ERROR: Could not locate GetSpeciesFormTable in src/pokemon.c")
    sys.exit(2)

block = m.group(1)

# Replace the "return SPECIES_NONE table" behavior with "return NULL"
block2 = re.sub(
    r'if\s*\(\s*formTable\s*==\s*NULL\s*\)\s*\n\s*return\s+gSpeciesInfo\s*\[\s*SPECIES_NONE\s*\]\.formSpeciesIdTable\s*;',
    'if (formTable == NULL)\n        return NULL;',
    block
)

if block2 == block:
    print("ERROR: Expected pattern not found inside GetSpeciesFormTable; no changes made.")
    print("Found block:\n", block[:400])
    sys.exit(3)

s2 = s[:m.start()] + block2 + s[m.end():]
open(path, "w", encoding="utf-8").write(s2)
print("OK: Patched GetSpeciesFormTable to return NULL when no form table exists.")
PY

echo
echo "Sanity check (show function):"
LINE=$(rg -n "GetSpeciesFormTable\\(u16 species\\)" -n src/pokemon.c | head -n1 | cut -d: -f1 || true)
if [[ -n "${LINE:-}" ]]; then
  START=$((LINE-5)); if [ $START -lt 1 ]; then START=1; fi
  END=$((LINE+25))
  sed -n "${START},${END}p" src/pokemon.c
else
  rg -n "GetSpeciesFormTable" src/pokemon.c | head -n 20
fi

echo
echo "Rebuild:"
make -j
