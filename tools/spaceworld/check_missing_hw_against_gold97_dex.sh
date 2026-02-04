#!/usr/bin/env bash
set -euo pipefail

GBROOT="${1:-$HOME/decomps/gold97}"
GBROOT="$(realpath "$GBROOT")"

DEX_MAIN="$GBROOT/data/pokemon/dex_entries.asm"
DEX_DIR="$GBROOT/data/pokemon/dex_entries"

[[ -f "$DEX_MAIN" ]] || { echo "ERROR: missing $DEX_MAIN" >&2; exit 1; }
[[ -d "$DEX_DIR"  ]] || { echo "ERROR: missing $DEX_DIR" >&2; exit 1; }

MISSING_LIST="/tmp/spaceworld_missing_hw.txt"
[[ -f "$MISSING_LIST" ]] || {
  echo "ERROR: missing $MISSING_LIST" >&2
  echo "Run: tools/spaceworld/report_spaceworld_missing_height_weight.sh | tee $MISSING_LIST" >&2
  exit 1
}

echo "GBROOT: $GBROOT"
echo "DEX_MAIN: $DEX_MAIN"
echo

# Extract dex include "mon names" like Abra from AbraPokedexEntry::
rg -n '^[A-Za-z0-9_]+PokedexEntry::\s+INCLUDE\s+"data/pokemon/dex_entries/[^"]+\.asm"' "$DEX_MAIN" \
  | sed -E 's/^.*\b([A-Za-z0-9_]+)PokedexEntry::.*$/\1/' \
  | tr '[:lower:]' '[:upper:]' \
  | sort -u > /tmp/gold97_dex_mons.txt

# Convert missing SPECIES_FOO_SPACEWORLD -> FOO
sed -E 's/^SPECIES_//; s/_SPACEWORLD$//' "$MISSING_LIST" \
  | sort -u > /tmp/missing_spaceworld_mons.txt

echo "== Missing SPACEWORLD mons that DO exist in gold97 dex list (name mismatch likely) =="
comm -12 /tmp/missing_spaceworld_mons.txt /tmp/gold97_dex_mons.txt || true
echo

echo "== Missing SPACEWORLD mons that do NOT exist in gold97 dex list (truly no dex entry there) =="
comm -23 /tmp/missing_spaceworld_mons.txt /tmp/gold97_dex_mons.txt || true
echo

echo "Wrote:"
echo "  /tmp/gold97_dex_mons.txt"
echo "  /tmp/missing_spaceworld_mons.txt"
