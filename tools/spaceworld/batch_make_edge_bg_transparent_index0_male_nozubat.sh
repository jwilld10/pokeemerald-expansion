#!/usr/bin/env bash
set -euo pipefail

root="graphics/spaceworld/pokemon"
skip="$root/zubat/anim_front.png"

count=0
changed=0
skipped=0
errors=0

echo "Batch fixing male anim_front.png under: $root"
echo "Skipping: $skip"
echo

while IFS= read -r -d '' f; do
  if [[ "$f" == "$skip" ]]; then
    echo "== [skip:zubat] $f"
    skipped=$((skipped+1))
    continue
  fi

  count=$((count+1))
  echo "== [$count] $f"

  # Run the tool, one file at a time (low memory / WSL-friendly)
  if python3 -u tools/spaceworld/make_edge_bg_transparent_dedicated_index.py "$f" --apply --to-index0; then
    :
  else
    echo "!! ERROR: $f"
    errors=$((errors+1))
  fi
done < <(find "$root" -type f -name 'anim_front.png' -print0)

echo
echo "Done."
echo "Processed: $count"
echo "Skipped:   $skipped"
echo "Errors:    $errors"
