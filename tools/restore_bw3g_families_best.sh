#!/bin/sh
set -eu

DIR="src/data/pokemon/species_info"
OUT="$DIR/bw3g_families.h"

# Pattern for the real species-info blocks
PATTERN='\[\s*SPECIES_[A-Z0-9_]+_BW3G\s*\]\s*=\s*\{'

# Collect backups that actually contain blocks, keeping mtime ordering
CANDIDATES="$(ls -1t "$DIR"/bw3g_families.h.bak_* 2>/dev/null || true)"
if [ -z "$CANDIDATES" ]; then
  echo "ERROR: No bw3g_families.h.bak_* backups found in $DIR"
  exit 1
fi

BEST=""
for f in $CANDIDATES; do
  if rg -q "$PATTERN" "$f"; then
    BEST="$f"
    break
  fi
done

if [ -z "$BEST" ]; then
  echo "ERROR: None of the backups contain BW3G species blocks."
  echo "Try widening search: maybe the blocks live in a different file name."
  echo
  echo "Backups checked:"
  printf "  %s\n" $CANDIDATES
  exit 1
fi

cp -f "$BEST" "$OUT"
echo "Restored BEST BW3G families backup:"
echo "  $BEST -> $OUT"

# Sanity counts
echo
echo "Sanity:"
echo -n "  BW3G blocks found: "
rg -c "$PATTERN" "$OUT" || true

echo -n "  First block key: "
rg -n "$PATTERN" "$OUT" | head -n 1 | sed 's/:.*//'
