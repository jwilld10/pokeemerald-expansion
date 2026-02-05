#!/usr/bin/env bash
set -euo pipefail
cd ~/decomps/pokeemerald-expansion_clean

OUT="tools/bw3g/_form_plumbing_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUT"
echo "Writing to: $OUT"

# Where is GetSpeciesFormTable declared/defined/used?
rg -n --no-heading "GetSpeciesFormTable\\(" src include > "$OUT/get_species_form_table_hits.out.txt" || true

# Try to extract the function body if it exists in src
python3 - <<'PY' > "$OUT/get_species_form_table_body.out.txt"
import re, glob
def read(p):
    with open(p,'r',encoding='utf-8',errors='replace') as f:
        return f.read()

found = 0
for p in glob.glob("src/**/*.c", recursive=True):
    s = read(p)
    if "GetSpeciesFormTable" not in s:
        continue
    m = re.search(r'(\w+\s+\*?\s*GetSpeciesFormTable\s*\([^)]*\)\s*\{.*?\n\})', s, flags=re.S)
    if m:
        found += 1
        print(f"--- {p} ---\n")
        print(m.group(1)[:12000])
        print("\n")

if found == 0:
    print("ERROR: Could not extract GetSpeciesFormTable body from src/**/*.c")
    print("Check hits file for where it is implemented (may be static, inline, macro, or generated).")
PY

# Also dump any obvious form table arrays
rg -n --no-heading "sSpeciesFormTable|SpeciesFormTable|gSpeciesForm|FormTable" src include \
  > "$OUT/form_table_arrays_hits.out.txt" || true

echo "DONE. Upload these:"
echo "  $OUT/get_species_form_table_hits.out.txt"
echo "  $OUT/get_species_form_table_body.out.txt"
echo "  $OUT/form_table_arrays_hits.out.txt"
ls -la "$OUT" > "$OUT/ls.txt"
