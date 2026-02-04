#!/bin/sh
set -eu

echo "== BW3G audit =="
python3 tools/audit_species_variant_flex.py BW3G src/data/pokemon/species_info/bw3g_families.h

echo
echo "== SPACEWORLD audit =="
python3 tools/audit_species_variant_flex.py SPACEWORLD src/data/pokemon/spaceworld_generated/spaceworld_species_info.h
