#!/usr/bin/env bash
set -euo pipefail

ROOT="${BW3G_PNG_ROOT:-$HOME/decomps/gb/BW3G/gfx/pokemon}"
DST="graphics/bw3g/pokemon"

echo "== BW3G PNG ROOT =="
echo "$ROOT"
echo

converted=0
skipped=0

for mon_dir in "$ROOT"/*; do
  [ -d "$mon_dir" ] || continue
  mon="$(basename "$mon_dir")"

  front="$mon_dir/front.png"
  back="$mon_dir/back.png"

  if [[ ! -f "$front" || ! -f "$back" ]]; then
    ((skipped++))
    continue
  fi

  outdir="$DST/$mon"
  mkdir -p "$outdir"

  if python3 tools/bw3g/png_to_gba_anim_front.py "$front" "$back" "$outdir" "$mon" >/dev/null; then
    ((converted++))
  else
    echo "SKIP: $mon (converter failed)"
    ((skipped++))
  fi
done

echo
echo "DONE: converted=$converted skipped=$skipped"
echo "Now rebuild: make -j"
