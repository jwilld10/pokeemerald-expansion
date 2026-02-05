#!/usr/bin/env bash
set -euo pipefail

FILE="tools/bw3g/rebuild_bw3g_from_pngs_spaceworld_style.sh"

if [[ ! -f "$FILE" ]]; then
  echo "ERROR: missing $FILE"
  exit 1
fi

cp -v "$FILE" "$FILE.bak_fixheredoc_$(date +%Y%m%d_%H%M%S)"

python3 - <<'PY'
import re, pathlib, sys
p = pathlib.Path("tools/bw3g/rebuild_bw3g_from_pngs_spaceworld_style.sh")
s = p.read_text(encoding="utf-8", errors="ignore")

# Replace the broken heredoc+redirect block with a correct one.
# We search for: python3 - <<'PY' "$FAMS" ... PY > /tmp/bw3g_sizes.map
pat = re.compile(
    r'python3\s+-\s+<<\'PY\'\s+"\$FAMS"\n'
    r'(.*?)\n'
    r'PY\s*>\s*/tmp/bw3g_sizes\.map\n',
    re.DOTALL
)

m = pat.search(s)
if not m:
    print("ERROR: Could not find the broken python heredoc block to fix.")
    sys.exit(1)

body = m.group(1)

fixed = (
    'python3 - "$FAMS" > /tmp/bw3g_sizes.map <<\'PY\'\n'
    + body + '\n'
    + 'PY\n'
)

s2 = s[:m.start()] + fixed + s[m.end():]
p.write_text(s2, encoding="utf-8")
print("OK: Fixed heredoc redirect in rebuild script.")
PY
