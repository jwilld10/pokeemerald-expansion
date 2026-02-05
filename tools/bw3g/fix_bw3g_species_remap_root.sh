#!/usr/bin/env bash
set -euo pipefail
cd ~/decomps/pokeemerald-expansion_clean

F="src/pokemon.c"
TS="$(date +%Y%m%d_%H%M%S)"
BAK="${F}.bak_bw3g_remapfix_${TS}"
cp -a "$F" "$BAK"
echo "Backup created: $BAK"

# Hard-code the BW3G anchor range (you already printed these successfully)
BW3G_MIN=2001   # SPECIES_SKARMORY_BW3G
BW3G_MAX=2054   # SPECIES_GENESECT_BW3G

python3 - <<PY
import re, sys

path = "src/pokemon.c"
s = open(path, "r", encoding="utf-8", errors="replace").read()
orig = s

# --- Patch 1: GetSpeciesFormTable should return NULL when no table exists ---
# Handle either "const u16 *" or "u16 *" return type.
m = re.search(r'((?:const\s+)?u16\s*\*\s*GetSpeciesFormTable\s*\(\s*u16\s+species\s*\)\s*\{.*?\n\})', s, flags=re.S)
if not m:
    print("ERROR: Could not find GetSpeciesFormTable(u16 species) function block")
    sys.exit(2)

block = m.group(1)

# Replace:
# if (formTable == NULL) return gSpeciesInfo[SPECIES_NONE].formSpeciesIdTable;
# with:
# if (formTable == NULL) return NULL;
block2, n = re.subn(
    r'if\s*\(\s*formTable\s*==\s*NULL\s*\)\s*\n\s*return\s+gSpeciesInfo\s*\[\s*SPECIES_NONE\s*\]\.formSpeciesIdTable\s*;',
    'if (formTable == NULL)\n        return NULL;',
    block
)

if n == 0:
    # If it's formatted differently, try a more flexible pattern (same meaning).
    block2, n = re.subn(
        r'if\s*\(\s*formTable\s*==\s*NULL\s*\)\s*\{?\s*\n\s*return\s+gSpeciesInfo\s*\[\s*SPECIES_NONE\s*\]\.formSpeciesIdTable\s*;\s*\n\s*\}?',
        'if (formTable == NULL)\n        return NULL;',
        block
    )

if n == 0:
    print("ERROR: Found GetSpeciesFormTable but did not find the SPECIES_NONE fallback return to replace.")
    print("First 300 chars of function for inspection:\n", block[:300])
    sys.exit(3)

s = s[:m.start()] + block2 + s[m.end():]

# --- Patch 2: Ensure BW3G species are treated as enabled ---
# Insert an early return TRUE in IsSpeciesEnabled(u16 species)
mi = re.search(r'(bool32\s+IsSpeciesEnabled\s*\(\s*u16\s+species\s*\)\s*\{)', s)
if not mi:
    print("ERROR: Could not find IsSpeciesEnabled(u16 species) signature")
    sys.exit(4)

insert = f"""
    // BW3G: treat BW3G species as enabled (prevents SanitizeSpeciesId -> SPECIES_NONE).
    if (species >= {int(BW3G_MIN)} && species <= {int(BW3G_MAX)})
        return TRUE;

"""
# Only insert if not already present
if "BW3G: treat BW3G species as enabled" not in s:
    s = s[:mi.end()] + insert + s[mi.end():]

open(path, "w", encoding="utf-8").write(s)

print("OK: patched GetSpeciesFormTable to return NULL, and IsSpeciesEnabled to allow BW3G range.")
PY

echo
echo "=== Verify patched snippets ==="
echo "--- GetSpeciesFormTable ---"
rg -n --no-heading "GetSpeciesFormTable\\(u16 species\\)" -n "$F" | head -n 2 || true
# show ~20 lines after first match
L=$(rg -n "GetSpeciesFormTable\\(u16 species\\)" "$F" | head -n1 | cut -d: -f1 || echo "")
if [[ -n "$L" ]]; then
  START=$((L)); END=$((L+22))
  sed -n "${START},${END}p" "$F"
fi

echo
echo "--- IsSpeciesEnabled (BW3G early return should appear) ---"
rg -n --no-heading "IsSpeciesEnabled\\(u16 species\\)|BW3G: treat BW3G species as enabled" "$F" | head -n 10 || true

echo
echo "=== Clean rebuild ==="
make clean
make -j

echo
echo "DONE. Test Genesect via debug menu again."
echo "If you need to revert: cp -a '$BAK' '$F' && make clean && make -j"
