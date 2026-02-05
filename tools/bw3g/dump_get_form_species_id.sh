#!/usr/bin/env bash
set -euo pipefail
cd ~/decomps/pokeemerald-expansion_clean

OUTDIR="tools/bw3g/_form_debug_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUTDIR"

echo "Writing outputs to: $OUTDIR"

# 1) All references (where it’s declared/used)
rg -n --no-heading "GetFormSpeciesId\\(" src include \
  > "$OUTDIR/get_form_species_id_hits.out.txt" || true

# 2) Try to extract the full function body from any src/*.c that defines it
python3 - <<'PY' > "$OUTDIR/get_form_species_id_body.out.txt"
import re, glob, os

def read(p):
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        return f.read()

printed = 0
for p in glob.glob("src/**/*.c", recursive=True):
    s = read(p)
    if "GetFormSpeciesId" not in s:
        continue

    # Match common signatures: u16 GetFormSpeciesId(...) { ... }
    m = re.search(r'(u16\s+GetFormSpeciesId\s*\([^)]*\)\s*\{.*?\n\})', s, flags=re.S)
    if m:
        printed += 1
        print(f"--- {p} ---\n")
        body = m.group(1)
        # Cap for sanity
        print(body[:12000])
        print("\n")

if printed == 0:
    print("ERROR: Could not find a 'u16 GetFormSpeciesId(...) { ... }' definition in src/**/*.c")
    print("It may be static, in a different return type, or generated. Check hits file for where it's defined.")
PY

echo "DONE."
echo "Files created:"
ls -la "$OUTDIR"
echo
echo "Upload these two files:"
echo "  $OUTDIR/get_form_species_id_hits.out.txt"
echo "  $OUTDIR/get_form_species_id_body.out.txt"
