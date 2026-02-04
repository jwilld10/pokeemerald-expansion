#!/bin/sh
set -eu

INC="include/data/text/species_names_bw3g.inc"
OUT="include/constants/species_bw3g.h"
SPECIES_H="include/constants/species.h"

if [ ! -f "$INC" ]; then
  echo "ERROR: missing $INC"
  exit 1
fi
if [ ! -f "$SPECIES_H" ]; then
  echo "ERROR: missing $SPECIES_H"
  exit 1
fi

mkdir -p "$(dirname "$OUT")"

TMP_SYMS="$(mktemp)"
trap 'rm -f "$TMP_SYMS"' EXIT

# Extract BW3G tokens from the .inc, unique in first-seen order.
# Filter out known non-species anchors like SPECIES_NAMES_BW3G if present.
rg -o 'SPECIES_[A-Z0-9_]+_BW3G' "$INC" \
  | awk '
      !seen[$0]++ {
        if ($0 == "SPECIES_NAMES_BW3G") next
        print
      }
    ' > "$TMP_SYMS"

COUNT="$(wc -l < "$TMP_SYMS" | tr -d " ")"
if [ "$COUNT" -lt 10 ]; then
  echo "ERROR: extracted only $COUNT BW3G symbols from $INC"
  echo "Check that $INC contains lines like: [SPECIES_FOO_BW3G] = _(\"Foo\"),"
  exit 1
fi

FIRST="$(head -n 1 "$TMP_SYMS")"
LAST="$(tail -n 1 "$TMP_SYMS")"

# Find last Spaceworld species define in species.h (strict suffix match)
# If you ever rename the suffix, update this.
LAST_SW="$(rg '^#define\s+SPECIES_[A-Z0-9_]+_(SW|SPACEWORLD)\b' "$SPECIES_H" | tail -n 1 | awk '{print $2}')"
if [ -z "${LAST_SW:-}" ]; then
  echo "ERROR: couldn't find last Spaceworld species in $SPECIES_H"
  exit 1
fi

{
  echo "#ifndef GUARD_CONSTANTS_SPECIES_BW3G_H"
  echo "#define GUARD_CONSTANTS_SPECIES_BW3G_H"
  echo
  echo "// Auto-generated from $INC"
  echo "// Appended after: $LAST_SW"
  echo

  prev="$LAST_SW"
  while IFS= read -r sym; do
    echo "#define $sym ($prev + 1)"
    prev="$sym"
  done < "$TMP_SYMS"

  echo
  echo "#endif // GUARD_CONSTANTS_SPECIES_BW3G_H"
} > "$OUT"

echo "Wrote $OUT"
echo "  Count: $COUNT"
echo "  First: $FIRST"
echo "  Last : $LAST"

# Patch SPECIES_EGG to follow the final BW3G species
if rg -q '^#define\s+SPECIES_EGG\b' "$SPECIES_H"; then
  # Replace the whole line regardless of previous RHS
  awk -v last="$LAST" '
    BEGIN { done=0 }
    $1=="#define" && $2=="SPECIES_EGG" {
      printf("#define SPECIES_EGG                                     (%s + 1)\n", last);
      done=1;
      next
    }
    { print }
    END {
      if (!done) exit 2
    }
  ' "$SPECIES_H" > "$SPECIES_H.tmp" && mv "$SPECIES_H.tmp" "$SPECIES_H"
  echo "Patched SPECIES_EGG to ($LAST + 1)"
else
  echo "WARNING: SPECIES_EGG not found in $SPECIES_H (left unchanged)"
fi
