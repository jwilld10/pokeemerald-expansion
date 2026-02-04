#!/bin/sh
set -eu

FILE="src/data/pokemon/species_info/bw3g_families.h"

if [ ! -f "$FILE" ]; then
  echo "ERROR: missing $FILE"
  exit 1
fi

# Backup
cp "$FILE" "$FILE.bak_fix_genesis_mon_$(date +%Y%m%d_%H%M%S)"

# Ensure the entry exists
if ! rg -n '^\s*\[\s*SPECIES_GENESIS_MON_BW3G\s*\]\s*=' "$FILE" >/dev/null; then
  echo "ERROR: SPECIES_GENESIS_MON_BW3G entry not found in $FILE"
  exit 1
fi

python3 - "$FILE" <<'PY'
import sys, re
from pathlib import Path

path = Path(sys.argv[1])
txt = path.read_text(encoding="utf-8", errors="ignore")

# Find start of the GENESIS_MON entry key line
m = re.search(r'(?m)^\s*\[\s*SPECIES_GENESIS_MON_BW3G\s*\]\s*=\s*$', txt)
if not m:
    raise SystemExit("Could not find key line for SPECIES_GENESIS_MON_BW3G")

# Find the opening '{' after it
m2 = re.search(r'\{', txt[m.end():])
if not m2:
    raise SystemExit("Could not find '{' after SPECIES_GENESIS_MON_BW3G key")
open_brace_idx = m.end() + m2.start()

# Find the end of that entry: the first line that matches '},' after the open brace
m3 = re.search(r'(?m)^\s*\},\s*$', txt[open_brace_idx:])
if not m3:
    raise SystemExit("Could not find end of SPECIES_GENESIS_MON_BW3G block (a line with '},')")
end_block_idx = open_brace_idx + m3.end()

block = txt[open_brace_idx:end_block_idx]

def has_field(name: str) -> bool:
    return re.search(r'(?m)^\s*\.' + re.escape(name) + r'\s*=', block) is not None

# Decide indentation: match existing field indentation if present, else default 8 spaces.
indent = "        "
m_indent = re.search(r'(?m)^(\s*)\.\w+\s*=', block)
if m_indent:
    indent = m_indent.group(1)

# Insert after the opening '{' line
lines = block.splitlines(True)

# Find insertion point: after the line containing '{'
insert_i = None
for i, line in enumerate(lines):
    if '{' in line:
        insert_i = i + 1
        break
if insert_i is None:
    raise SystemExit("Internal error: couldn't locate '{' line for insertion")

stub_lines = []

# Core gameplay-ish fields your audit expects
core = [
    ("baseHP", "1"),
    ("baseAttack", "1"),
    ("baseDefense", "1"),
    ("baseSpeed", "1"),
    ("baseSpAttack", "1"),
    ("baseSpDefense", "1"),
    ("types", "{ TYPE_NORMAL, TYPE_NORMAL }"),
    ("catchRate", "3"),
    ("expYield", "1"),
    ("iconSprite", "gBw3gMonIcon_GenesisMon"),
    ("iconPalIndex", "7"),
    ("categoryName", '_("GENESIS")'),
    ("height", "1"),
    ("weight", "1"),
    ("levelUpLearnset", "sEmptyLevelUpLearnset"),
]

for k, v in core:
    if not has_field(k):
        stub_lines.append(f"{indent}.{k} = {v},\n")

# If nothing to do, exit cleanly
if not stub_lines:
    print("No changes needed: GENESIS_MON already has all required fields.")
    sys.exit(0)

# Insert the stub lines near the top of the entry
new_lines = lines[:insert_i] + stub_lines + lines[insert_i:]
new_block = "".join(new_lines)

new_txt = txt[:open_brace_idx] + new_block + txt[end_block_idx:]
path.write_text(new_txt, encoding="utf-8")

print(f"Patched {path} (added {len(stub_lines)} missing fields to SPECIES_GENESIS_MON_BW3G)")
PY

echo "Done."
echo "Now run:"
echo "  python3 tools/audit_species_variant_flex.py BW3G $FILE"
