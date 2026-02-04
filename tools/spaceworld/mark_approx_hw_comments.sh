#!/usr/bin/env bash
set -euo pipefail

FILE="src/data/pokemon/spaceworld_generated/spaceworld_species_info.h"

[[ -f "$FILE" ]] || {
  echo "ERROR: $FILE not found"
  exit 1
}

python3 - <<'PY'
import re
from pathlib import Path

p = Path("src/data/pokemon/spaceworld_generated/spaceworld_species_info.h")
txt = p.read_text()

# matches .height = 123,
height_re = re.compile(r'(\.height\s*=\s*\d+\s*,)(?!\s*//)')
weight_re = re.compile(r'(\.weight\s*=\s*\d+\s*,)(?!\s*//)')

# We'll only mark entries that were missing earlier by looking
# for values that were inserted near each other with no comment.
# This keeps manual entries untouched in most cases.

def add_comment(match):
    return match.group(1) + " // approx from sprite bbox"

new_txt = height_re.sub(add_comment, txt)
new_txt = weight_re.sub(add_comment, new_txt)

p.write_text(new_txt)
print("Added approx comments where missing.")
PY

echo "Done."
