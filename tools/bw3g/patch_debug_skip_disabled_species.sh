#!/usr/bin/env bash
set -euo pipefail
cd ~/decomps/pokeemerald-expansion_clean

F="src/debug.c"
TS="$(date +%Y%m%d_%H%M%S)"
BAK="${F}.bak_skip_disabled_${TS}"
cp -a "$F" "$BAK"
echo "Backup: $BAK"

python3 - <<'PY'
import re, sys

path = "src/debug.c"
s = open(path, "r", encoding="utf-8", errors="replace").read()

# 1) Ensure we have a helper that finds the next enabled species.
helper_name = "Debug_GetNextEnabledSpecies"
if helper_name not in s:
    insert_point = s.find("#define tInput")
    if insert_point == -1:
        print("ERROR: couldn't find '#define tInput' anchor in debug.c")
        sys.exit(2)

    helper = r'''
static u16 Debug_GetNextEnabledSpecies(u16 species, s8 dir)
{
    // Walk at most NUM_SPECIES times to avoid infinite loops.
    for (u16 i = 0; i <= NUM_SPECIES; i++)
    {
        // move
        if (dir >= 0)
        {
            species++;
            if (species > NUM_SPECIES)
                species = 1;
        }
        else
        {
            if (species <= 1)
                species = NUM_SPECIES;
            else
                species--;
        }

        if (IsSpeciesEnabled(species))
            return species;
    }
    return SPECIES_NONE;
}
'''
    s = s[:insert_point] + helper + "\n" + s[insert_point:]
    print("Inserted Debug_GetNextEnabledSpecies helper.")

# 2) Patch Debug_Display_SpeciesInfo to “snap” to an enabled species
m = re.search(r'void\s+Debug_Display_SpeciesInfo\s*\(\s*u8\s+taskId\s*,.*?\)\s*\{', s)
if not m:
    print("ERROR: couldn't find Debug_Display_SpeciesInfo(...) definition")
    sys.exit(3)

brace_end = m.end()
inject = r'''
    // If current species is disabled, advance to next enabled species
    if (!IsSpeciesEnabled(gTasks[taskId].tInput))
        gTasks[taskId].tInput = Debug_GetNextEnabledSpecies(gTasks[taskId].tInput, +1);

'''
# Only inject once
window = s[brace_end:brace_end+300]
if "advance to next enabled species" not in window:
    s = s[:brace_end] + inject + s[brace_end:]
    print("Patched Debug_Display_SpeciesInfo to skip disabled species.")

open(path, "w", encoding="utf-8").write(s)
print("OK")
PY

echo
echo "Rebuild:"
make -j
echo
echo "DONE. Debug species list should now skip disabled IDs instead of showing ????"
echo "Revert: cp -a '$BAK' '$F' && make -j"
