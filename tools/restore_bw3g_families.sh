#!/bin/sh
set -eu

DIR="src/data/pokemon/species_info"
BASE="$DIR/bw3g_families.h"

# Find newest backup by mtime
NEWEST="$(ls -1t "$DIR"/bw3g_families.h.bak_* 2>/dev/null | head -n 1 || true)"
if [ -z "$NEWEST" ]; then
  echo "ERROR: no bw3g_families.h.bak_* found in $DIR"
  exit 1
fi

cp -f "$NEWEST" "$BASE"
echo "Restored:"
echo "  $NEWEST -> $BASE"

# Quick sanity: does it contain BW3G blocks?
if rg -q '\[\s*SPECIES_[A-Z0-9_]+_BW3G\s*\]\s*=\s*\{' "$BASE"; then
  echo "OK: BW3G species blocks found in restored file."
else
  echo "WARNING: restored file does not appear to contain BW3G species blocks."
  echo "You may have restored a non-block variant; check the other backups."
fi
