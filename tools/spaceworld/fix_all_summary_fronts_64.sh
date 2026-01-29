#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(pwd)"
SCRIPT="$REPO_ROOT/tools/spaceworld/fix_summary_pic_box_and_center_64.py"

# one-by-one processing (avoids xargs burst crashes)
while IFS= read -r -d '' f; do
  "$SCRIPT" "$f" --apply
done < <(find graphics/spaceworld/pokemon -type f -name 'anim_front.png' -print0)
