#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-$PWD}"

cd "$ROOT"

echo "== Repo =="
pwd
echo

echo "============================================================"
echo "1) pokemon_icon.c: BW3G hooks + key functions"
echo "============================================================"
FILE="src/pokemon_icon.c"
if [[ ! -f "$FILE" ]]; then
  echo "ERROR: $FILE not found"
  exit 1
fi

echo "-- Includes mentioning bw3g / icon table --"
rg -n --no-heading "bw3g|Bw3g|BW3G|mon_icons_table|icons_table_generated" "$FILE" || true
echo

echo "-- Functions of interest in pokemon_icon.c (signatures + line numbers) --"
rg -n --no-heading "^(static\s+)?(const\s+)?(u8|u16|u32|void|bool8|const\s+u8|const\s+u16|const\s+u32).*\b(GetMonIconTiles|GetValidMonIconPalettePtr|CreateMonIcon|CreateMonIconNoPersonality|GetMonIconPtr|LoadMonIconPalette|LoadMonIconPalettes|UpdateMonIcon|CreateMonIconSprite|GetMonIconSpriteId)\b" "$FILE" || true
echo

echo "-- Extract full bodies for common icon functions (best-effort awk extractor) --"
extract_func () {
  local func="$1"
  echo "----- BEGIN FUNCTION: $func -----"
  awk -v fn="$func" '
    BEGIN{found=0; depth=0;}
    {
      if (!found) {
        # match "func(" in a C-ish function definition line
        if ($0 ~ fn "\\(") {
          found=1
        }
      }
      if (found) {
        print
        # crude brace tracking
        n=gsub(/{/,"{")
        depth+=n
        n=gsub(/}/,"}")
        depth-=n
        if (depth<=0 && $0 ~ /}/) {
          exit
        }
      }
    }
  ' "$FILE" || true
  echo "----- END FUNCTION: $func -----"
  echo
}

# These are the ones you said you modified / that usually control the crash/fallback
for fn in \
  GetMonIconTiles \
  GetValidMonIconPalettePtr \
  CreateMonIcon \
  CreateMonIconNoPersonality \
  UpdateMonIcon \
  LoadMonIconPalette \
  LoadMonIconPalettes \
  GetMonIconPtr \
  CreateMonIconSprite \
  GetMonIconSpriteId
do
  extract_func "$fn"
done

echo "============================================================"
echo "2) Species validity / sanitization (possible Bulbasaur fallback)"
echo "============================================================"

# Search likely locations
CANDIDATES=(
  "src"
  "include"
)

echo "-- Places referencing SanitizeSpeciesId / IsSpeciesValid / NUM_SPECIES style guards --"
rg -n --no-heading "SanitizeSpeciesId|IsSpeciesValid|IsValidSpecies|NUM_SPECIES|SPECIES_EGG|SPECIES_NONE|SPECIES_BULBASAUR" "${CANDIDATES[@]}" || true
echo

echo "-- Try to locate function bodies for SanitizeSpeciesId / IsSpeciesValid --"
# Find the file/line of definition candidates
rg -n --no-heading "^\s*(static\s+)?(u16|u32|bool8)\s+(SanitizeSpeciesId|IsSpeciesValid|IsValidSpecies)\s*\(" src include || true
echo

# Extract bodies if we find obvious definitions
# This is a little broad; it prints the first match in each file.
while IFS= read -r hit; do
  f="$(echo "$hit" | cut -d: -f1)"
  name="$(echo "$hit" | sed -E 's/.*\b(SanitizeSpeciesId|IsSpeciesValid|IsValidSpecies)\s*\(.*/\1/')"
  echo "----- BEGIN DEF: $name in $f -----"
  awk -v fn="$name" '
    BEGIN{found=0; depth=0;}
    {
      if (!found) {
        if ($0 ~ fn "\\(") { found=1 }
      }
      if (found) {
        print
        n=gsub(/{/,"{"); depth+=n
        n=gsub(/}/,"}"); depth-=n
        if (depth<=0 && $0 ~ /}/) { exit }
      }
    }
  ' "$f" || true
  echo "----- END DEF: $name in $f -----"
  echo
done < <(rg -n "^\s*(static\s+)?(u16|u32|bool8)\s+(SanitizeSpeciesId|IsSpeciesValid|IsValidSpecies)\s*\(" src include || true)

echo "============================================================"
echo "3) BW3G species block: confirm icon fields + pal index + ranges"
echo "============================================================"

BW3G_FAM="src/data/pokemon/species_info/bw3g_families.h"
if [[ -f "$BW3G_FAM" ]]; then
  echo "-- bw3g_families.h: first ~120 lines --"
  sed -n '1,120p' "$BW3G_FAM"
  echo

  echo "-- bw3g_families.h: find iconPalIndex / iconSprite usage --"
  rg -n --no-heading "iconPalIndex|iconSprite|gBw3gMonIcon|BW3G" "$BW3G_FAM" || true
  echo
else
  echo "WARN: $BW3G_FAM not found"
fi

echo "============================================================"
echo "4) BW3G icon table header: where it comes from"
echo "============================================================"
rg -n --no-heading "bw3g_mon_icons_table_generated\.h|Bw3gMonIconTable|sBw3gMonIconTable|gBw3gMonIcon" src include data || true
echo

echo "============================================================"
echo "DONE"
echo "Copy all output and paste it back here."
