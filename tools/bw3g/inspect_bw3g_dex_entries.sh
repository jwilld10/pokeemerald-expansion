#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-$HOME/decomps/gb/BW3G}"
ROOT="$(realpath "$ROOT")"

DEX_MAIN="$ROOT/data/pokemon/dex_entries.asm"
DEX_DIR="$ROOT/data/pokemon/dex_entries"

[[ -f "$DEX_MAIN" ]] || { echo "ERROR: missing $DEX_MAIN" >&2; exit 1; }
[[ -d "$DEX_DIR"  ]] || { echo "ERROR: missing $DEX_DIR" >&2; exit 1; }

echo "ROOT: $ROOT"
echo "DEX_MAIN: $DEX_MAIN"
echo "DEX_DIR:  $DEX_DIR"
echo

echo "== INCLUDE list (first 60) =="
sed -n '1,80p' "$DEX_MAIN" | nl -ba | head -n 60
echo

echo "== Count dex entry include files =="
count_includes=$(rg -n 'INCLUDE\s+"data/pokemon/dex_entries/[^"]+\.asm"' "$DEX_MAIN" | wc -l | tr -d ' ')
count_files=$(find "$DEX_DIR" -maxdepth 1 -type f -name '*.asm' | wc -l | tr -d ' ')
echo "INCLUDES in dex_entries.asm: $count_includes"
echo "FILES in dex_entries/:        $count_files"
echo

echo "== Any includes missing on disk? =="
tmp_inc="$(mktemp)"
tmp_fs="$(mktemp)"
rg -o 'data/pokemon/dex_entries/[^"]+\.asm' "$DEX_MAIN" | sort -u > "$tmp_inc"
(cd "$ROOT" && find data/pokemon/dex_entries -maxdepth 1 -type f -name '*.asm' | sort -u) > "$tmp_fs"

missing=$(comm -23 "$tmp_inc" "$tmp_fs" || true)
if [[ -n "$missing" ]]; then
  echo "$missing" | sed 's/^/MISSING: /'
else
  echo "None."
fi
echo

echo "== Show 3 sample entry files (first 120 lines each) =="
# pick 3 deterministic examples that should exist early in the list
for f in snivy servine serperior; do
  p="$DEX_DIR/$f.asm"
  echo
  echo "--- $p ---"
  if [[ -f "$p" ]]; then
    sed -n '1,120p' "$p" | nl -ba
  else
    echo "NOT FOUND"
  fi
done

echo
echo "== Quick format sniff across dex_entries/*.asm =="
echo "Top patterns:"
rg -h --no-filename -S '^\s*(db|dw|dn|text|ctxt|next|page|para|dexentry|entry)\b' "$DEX_DIR" \
  | sed -E 's/^\s+//' | cut -c1-60 | sort | uniq -c | sort -nr | head -n 30

rm -f "$tmp_inc" "$tmp_fs"
