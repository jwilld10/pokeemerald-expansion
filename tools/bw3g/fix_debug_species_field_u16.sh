#!/usr/bin/env bash
set -euo pipefail
cd ~/decomps/pokeemerald-expansion_clean

F="src/debug.c"
TS="$(date +%Y%m%d_%H%M%S)"
BAK="${F}.bak_fixspecies_${TS}"
cp -a "$F" "$BAK"
echo "Backup created: $BAK"

python3 - <<'PY'
import re, sys
path = "src/debug.c"
s = open(path, "r", encoding="utf-8", errors="replace").read()

m = re.search(r'\bstruct\s+DebugMonData\s*\{.*?\n\};', s, flags=re.S)
if not m:
    print("ERROR: struct DebugMonData not found")
    sys.exit(2)

block = m.group(0)

# Change only the species field, only if it is u8.
block2, n = re.subn(r'(^\s*)u8(\s+species\s*;)', r'\1u16\2', block, flags=re.M)

if n == 0:
    # already u16 or different name; print what we found for species line
    species_lines = re.findall(r'^\s*(u8|u16|u32)\s+species\s*;', block, flags=re.M)
    if species_lines:
        print("No change needed; species already:", species_lines[0])
        sys.exit(0)
    print("ERROR: Found struct DebugMonData but couldn't find a 'u8 species;' field.")
    # Dump any line containing 'species' inside the struct to help next patch
    for line in block.splitlines():
        if 'species' in line:
            print("STRUCT LINE:", line)
    sys.exit(3)

s2 = s[:m.start()] + block2 + s[m.end():]
open(path, "w", encoding="utf-8").write(s2)
print("OK: changed 'u8 species;' -> 'u16 species;' inside struct DebugMonData")
PY

echo
echo "Sanity check (show species line + give call):"
rg -n --no-heading "struct DebugMonData|u16\\s+species\\s*;|ScriptGiveMon\\(sDebugMonData->species" src/debug.c | head -n 60 || true
