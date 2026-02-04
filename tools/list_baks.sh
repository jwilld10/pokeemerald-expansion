#!/bin/sh
set -eu

echo "=== Newest .bak_* per file (with sizes) ==="
find src include -type f -name "*.bak_*" -print0 \
| while IFS= read -r -d '' f; do
    base="${f%%.bak_*}"
    # mtime epoch + path
    printf '%s\t%s\t%s\n' "$(stat -c '%Y' "$f")" "$base" "$f"
  done \
| sort -n \
| awk -F'\t' '
  { newest[$2]=$0 }
  END {
    for (b in newest) print newest[b]
  }' \
| sort -n \
| while IFS="$(printf '\t')" read -r epoch base bak; do
    cur="(missing)"
    cursz="NA"
    if [ -f "$base" ]; then
      cursz=$(stat -c '%s' "$base")
      cur="$base"
    fi
    baksz=$(stat -c '%s' "$bak")
    # show date, current size, bak size, file paths
    printf '%s  cur:%8s  bak:%8s  %s  <-  %s\n' \
      "$(date -d "@$epoch" '+%F %T')" "$cursz" "$baksz" "$cur" "$bak"
  done
