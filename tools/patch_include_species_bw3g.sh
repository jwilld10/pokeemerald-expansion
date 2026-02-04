#!/usr/bin/env bash
set -euo pipefail

FILE="include/constants/species.h"

if [[ ! -f "$FILE" ]]; then
  echo "ERROR: $FILE not found"
  exit 1
fi

if rg -q '^\s*#include\s+"constants/species_bw3g\.h"\s*$' "$FILE"; then
  echo "Already included: constants/species_bw3g.h"
  exit 0
fi

tmp="$(mktemp)"
awk '
BEGIN{added=0}
{
  print $0
  # insert after an include cluster of constants/species_*.h, but only once
  if (!added && $0 ~ /^[[:space:]]*#include[[:space:]]+"constants\/species_[^"]+\.h"[[:space:]]*$/) {
    last_include_line=NR
  }
}
END{}
' "$FILE" > "$tmp"

# Now do a second pass to insert after the last include in that cluster.
python3 - <<'PY'
from pathlib import Path
import re

file = Path("include/constants/species.h")
lines = file.read_text(encoding="utf-8").splitlines(True)

pat = re.compile(r'^\s*#include\s+"constants/species_[^"]+\.h"\s*$')
last = None
for i,ln in enumerate(lines):
    if pat.match(ln.rstrip("\n")):
        last = i

if last is None:
    raise SystemExit("ERROR: no #include \"constants/species_*.h\" lines found to anchor insertion")

ins = '#include "constants/species_bw3g.h"\n'
lines.insert(last+1, ins)
file.write_text("".join(lines), encoding="utf-8")
print(f"Patched {file}: inserted species_bw3g.h after line {last+1}")
PY

echo "Done."
