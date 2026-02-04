#!/usr/bin/env bash
set -euo pipefail

SPECIES_H="include/constants/species.h"

[[ -f "$SPECIES_H" ]] || { echo "ERROR: missing $SPECIES_H" >&2; exit 1; }

need_bw3g='^#include "constants/species_bw3g\.h"$'
need_sw='^#include "constants/species_spaceworld\.h"$'

has_bw3g=0
has_sw=0

if rg -q "$need_bw3g" "$SPECIES_H"; then has_bw3g=1; fi
if rg -q "$need_sw" "$SPECIES_H"; then has_sw=1; fi

# Only insert spaceworld include if that header actually exists
want_sw=0
if [[ -f "include/constants/species_spaceworld.h" ]]; then
  want_sw=1
fi

python3 - <<'PY'
from pathlib import Path
import re

species_h = Path("include/constants/species.h")
txt = species_h.read_text(encoding="utf-8", errors="ignore").splitlines(True)

# Find spot right after:
# #define GUARD_CONSTANTS_SPECIES_H
guard_pat = re.compile(r'^\s*#define\s+GUARD_CONSTANTS_SPECIES_H\s*$')

insert_at = None
for i, line in enumerate(txt):
    if guard_pat.match(line.rstrip("\n")):
        insert_at = i + 1
        break

if insert_at is None:
    raise SystemExit("ERROR: Could not find '#define GUARD_CONSTANTS_SPECIES_H' in include/constants/species.h")

def has_line(s):
    return any(l.rstrip("\n") == s for l in txt)

to_insert = []
if not has_line('#include "constants/species_bw3g.h"'):
    to_insert.append('#include "constants/species_bw3g.h"\n')

# Only add spaceworld include if file exists
if Path("include/constants/species_spaceworld.h").exists():
    if not has_line('#include "constants/species_spaceworld.h"'):
        to_insert.append('#include "constants/species_spaceworld.h"\n')

if not to_insert:
    print("No changes needed (variant includes already present).")
else:
    # keep a blank line after inserted includes if not already there
    block = "".join(to_insert)
    # insert with a trailing newline for readability
    block += "\n"
    txt.insert(insert_at, block)
    species_h.write_text("".join(txt), encoding="utf-8")
    print(f"Patched {species_h}: inserted {len(to_insert)} include(s) after GUARD_CONSTANTS_SPECIES_H.")
PY

echo "Done."
