#!/usr/bin/env bash
set -euo pipefail

REPO="${1:-$HOME/mega_crystal_world/pokeemerald-expansion_clean}"

cd "$REPO"

# Re-generate Spaceworld files first (if present)
if [[ -f "$HOME/scripts/spaceworld/integrate_spaceworld.py" ]]; then
  python3 "$HOME/scripts/spaceworld/integrate_spaceworld.py" || true
fi

make -j2 > build.log 2>&1 || true

# Keep it pasteable: show top unique errors + top fatal errors + file/line distribution
{
  echo "== TOP fatal errors (first 60) =="
  rg -n "fatal error:" build.log | head -n 60 || true
  echo
  echo "== TOP errors (first 120) =="
  rg -n "(^|: )error:" build.log | head -n 120 || true
  echo
  echo "== UNIQUE error messages (first 80) =="
  rg -o "fatal error: .*|error: .*" build.log | sort | uniq | head -n 80 || true
  echo
  echo "== MOST common error locations (top 30) =="
  rg -n "(fatal error:|error:)" build.log \
    | sed -E 's/:([0-9]+):.*$/:LINE/' \
    | awk -F: '{print $1 ":" $2}' \
    | sort | uniq -c | sort -nr | head -n 30 || true
} > build.summary.txt

echo "WROTE: $REPO/build.summary.txt"
echo "TIP: paste build.summary.txt contents here"
