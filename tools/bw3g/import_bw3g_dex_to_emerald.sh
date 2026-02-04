#!/usr/bin/env bash
set -euo pipefail

BW3G_ROOT="${1:-$HOME/decomps/gb/BW3G}"
FAMILIES_H="${2:-src/data/pokemon/species_info/bw3g_families.h}"
OUT_H="${3:-src/data/pokemon/bw3g_generated/bw3g_pokedex_text.h}"

BW3G_ROOT="$(realpath "$BW3G_ROOT")"

python3 tools/bw3g/import_bw3g_dex_to_emerald.py "$BW3G_ROOT" "$FAMILIES_H" "$OUT_H"

echo
echo "Done."
echo "Now re-audit BW3G:"
echo "  python3 tools/audit_species_variant_flex.py BW3G $FAMILIES_H"
