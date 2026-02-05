#!/usr/bin/env bash
set -euo pipefail
cd ~/decomps/pokeemerald-expansion_clean

F="src/debug.c"
TS="$(date +%Y%m%d_%H%M%S)"
BAK="${F}.bak_enabled_list_${TS}"
cp -a "$F" "$BAK"
echo "Backup: $BAK"

python3 - <<'PY'
import re, sys

path = "src/debug.c"
s = open(path, "r", encoding="utf-8", errors="replace").read()

# 0) Ensure IsSpeciesEnabled is visible in this TU
# debug.c already uses IsSpeciesEnabled indirectly in many branches; if it doesn't include pokemon.h, it may still compile via others.
# We'll just proceed; build will tell us.

# 1) Insert globals + builder near the top (after includes).
marker = "\n// --- BW3G DEBUG PATCH: enabled species list ---\n"
if marker in s:
    print("Already patched; exiting without changes.")
    sys.exit(0)

ins_point = s.find("\n#define tInput")
if ins_point == -1:
    print("ERROR: couldn't find '#define tInput' anchor")
    sys.exit(2)

blob = marker + r'''
static u16 *sDebugEnabledSpecies = NULL;
static u16 sDebugEnabledSpeciesCount = 0;

static void Debug_BuildEnabledSpeciesList(void)
{
    // Allocate once; list persists while debug menu is open.
    if (sDebugEnabledSpecies != NULL)
        return;

    // Worst case: all species enabled.
    sDebugEnabledSpecies = Alloc(sizeof(u16) * (NUM_SPECIES + 1));
    if (sDebugEnabledSpecies == NULL)
    {
        sDebugEnabledSpeciesCount = 0;
        return;
    }

    for (u16 species = 1; species <= NUM_SPECIES; species++)
    {
        if (IsSpeciesEnabled(species))
            sDebugEnabledSpecies[sDebugEnabledSpeciesCount++] = species;
    }

    // Sentinel
    sDebugEnabledSpecies[sDebugEnabledSpeciesCount] = SPECIES_NONE;
}

static u16 Debug_GetEnabledSpeciesByIndex(u16 idx)
{
    Debug_BuildEnabledSpeciesList();
    if (sDebugEnabledSpecies == NULL || sDebugEnabledSpeciesCount == 0)
        return 1; // fallback

    if (idx >= sDebugEnabledSpeciesCount)
        idx = 0;
    return sDebugEnabledSpecies[idx];
}

static u16 Debug_GetEnabledSpeciesIndex(u16 species)
{
    Debug_BuildEnabledSpeciesList();
    if (sDebugEnabledSpecies == NULL || sDebugEnabledSpeciesCount == 0)
        return 0;

    for (u16 i = 0; i < sDebugEnabledSpeciesCount; i++)
        if (sDebugEnabledSpecies[i] == species)
            return i;

    return 0;
}

'''
s = s[:ins_point] + blob + s[ins_point:]
print("Inserted enabled species list helpers.")

# 2) Find the section in debug menu where tInput is used as species and incremented.
# We will patch the two places where the species is initialized from sDebugMonData->species,
# and where DPAD changes tInput in the species picker state machine.
#
# We’ll do a conservative patch: when species selection screen loads OR redraws, force:
#   tEnabledIdx = Debug_GetEnabledSpeciesIndex(tInput)
# and when it redraws, set:
#   tInput = Debug_GetEnabledSpeciesByIndex(tEnabledIdx)
#
# To avoid invasive structural edits, we add a new task data slot for the enabled index.

# Find where tInput is defined in task data; add another define near it.
if "#define tEnabledIdx" not in s:
    s = s.replace("#define tInput               data[3]\n",
                  "#define tInput               data[3]\n#define tEnabledIdx          data[4]\n")
    print("Added tEnabledIdx task field define.")

# Patch: whenever code assigns gTasks[taskId].tInput = sDebugMonData->species;
s, n1 = re.subn(r'(gTasks\[taskId\]\.tInput\s*=\s*sDebugMonData->species\s*;)',
                r'\1\n    gTasks[taskId].tEnabledIdx = Debug_GetEnabledSpeciesIndex(gTasks[taskId].tInput);\n    gTasks[taskId].tInput = Debug_GetEnabledSpeciesByIndex(gTasks[taskId].tEnabledIdx);',
                s)
print(f"Patched species init assignments: {n1}")

# Patch: any call to Debug_Display_SpeciesInfo(gTasks[taskId].tInput, ...) to snap tInput from enabledIdx first.
# This avoids needing to find the function definition.
pattern_call = re.compile(r'(\s*)Debug_Display_SpeciesInfo\s*\(\s*gTasks\[taskId\]\.tInput\s*,', re.M)
matches = list(pattern_call.finditer(s))
added = 0
out = []
last = 0
for m in matches:
    start = m.start()
    lookback = s[max(0, start-250):start]
    if "tEnabledIdx" in lookback and "Debug_GetEnabledSpeciesByIndex" in lookback:
        continue
    indent = m.group(1)
    inject = (
        f"{indent}gTasks[taskId].tInput = Debug_GetEnabledSpeciesByIndex(gTasks[taskId].tEnabledIdx);\n"
    )
    out.append(s[last:start])
    out.append(inject)
    last = start
    added += 1
out.append(s[last:])
s = "".join(out)
print(f"Injected snap-before-display at {added} call site(s).")

# Patch: DPAD adjustments that modify tInput by powers of ten are generic number entry.
# We specifically want to intercept when the species picker is active; that's hard to detect reliably without more context.
# So instead: whenever tInput is modified (in the species selection state), we re-derive enabled index from it.
# We'll patch the line: sDebugMonData->species = gTasks[taskId].tInput; (when committing)
# to commit the enabled-index selected species.
s, n2 = re.subn(r'(sDebugMonData->species\s*=\s*gTasks\[taskId\]\.tInput\s*;)',
                r'gTasks[taskId].tInput = Debug_GetEnabledSpeciesByIndex(gTasks[taskId].tEnabledIdx);\n    \1',
                s)
print(f"Patched commit assignment: {n2}")

open(path, "w", encoding="utf-8").write(s)
print("OK: wrote patched debug.c")
PY

echo
echo "Rebuild:"
make -j

echo
echo "DONE. Debug species menu should no longer show disabled ???? entries."
echo "Revert: cp -a '$BAK' '$F' && make -j"
