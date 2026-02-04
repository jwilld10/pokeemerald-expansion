#!/usr/bin/env bash
set -euo pipefail

F="src/data/pokemon/species_info/bw3g_families.h"
GEN_H="src/data/pokemon/bw3g_generated/bw3g_pokedex_text.h"

[[ -f "$F" ]] || { echo "ERROR: missing $F" >&2; exit 1; }

echo "== Removing .pokedexNum lines from BW3G families file =="
# Remove any .pokedexNum = ... lines (keeps formatting stable enough)
# Handles indentation and optional trailing comments.
perl -0777 -i -pe 's/^\s*\.pokedexNum\s*=\s*[^,\n]+,\s*\n//mg' "$F"

echo "== Ensuring Genesis Mon has a description string available =="
mkdir -p "$(dirname "$GEN_H")"
if [[ ! -f "$GEN_H" ]]; then
  cat > "$GEN_H" <<'H'
// Auto-generated (minimal): BW3G dex text stubs
#ifndef GUARD_BW3G_POKEDEX_TEXT_H
#define GUARD_BW3G_POKEDEX_TEXT_H

#include "global.h"

static const u8 gBw3gPokedexText_GenesisMon[] = _("A mysterious prototype Pokémon.");

#endif // GUARD_BW3G_POKEDEX_TEXT_H
H
else
  # Add the Genesis Mon text constant if it doesn't exist yet
  if ! rg -q 'gBw3gPokedexText_GenesisMon' "$GEN_H"; then
    perl -0777 -i -pe 's/(#include "global\.h"\s*\n)/$1\nstatic const u8 gBw3gPokedexText_GenesisMon[] = _("A mysterious prototype Pokémon.");\n/s' "$GEN_H"
  fi
fi

echo "== Ensuring bw3g_families includes the generated dex text header =="
if ! rg -q 'data/pokemon/bw3g_generated/bw3g_pokedex_text\.h' "$F"; then
  perl -0777 -i -pe 's/(#define\s+GUARD_[A-Z0-9_]+\s*\n)/$1#include "data\/pokemon\/bw3g_generated\/bw3g_pokedex_text.h"\n/s' "$F"
fi

echo "== Ensuring SPECIES_GENESIS_MON_BW3G has a .description field =="
python3 - <<'PY'
from pathlib import Path
import re

p = Path("src/data/pokemon/species_info/bw3g_families.h")
txt = p.read_text(encoding="utf-8", errors="ignore")

# Find the GENESIS MON entry block
start_re = re.compile(r'^\s*\[\s*SPECIES_GENESIS_MON_BW3G\s*\]\s*=\s*$', re.M)
m = start_re.search(txt)
if not m:
    raise SystemExit("ERROR: couldn't find SPECIES_GENESIS_MON_BW3G block")

start = m.end()
# block ends at next "[SPECIES_" or EOF
next_re = re.compile(r'^\s*\[\s*SPECIES_[A-Z0-9_]+_BW3G\s*\]\s*=\s*$', re.M)
m2 = next_re.search(txt, start)
end = m2.start() if m2 else len(txt)

block = txt[start:end]

has_desc = re.search(r'^\s*\.description\s*=\s*', block, re.M) is not None
if has_desc:
    print("Genesis Mon already has .description")
    raise SystemExit(0)

# Insert before closing "},"
close = re.search(r'^\s*\},\s*$', block, re.M)
if not close:
    raise SystemExit("ERROR: couldn't find closing '},' for Genesis Mon block")

ins = "        .description = gBw3gPokedexText_GenesisMon,\n"
block2 = block[:close.start()] + ins + block[close.start():]

txt2 = txt[:start] + block2 + txt[end:]
p.write_text(txt2, encoding="utf-8")
print("Patched Genesis Mon .description")
PY

echo
echo "Done. Re-audit:"
echo "  python3 tools/audit_species_variant_flex.py BW3G $F"
