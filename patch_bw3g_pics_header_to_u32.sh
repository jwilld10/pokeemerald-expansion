#!/usr/bin/env bash
set -euo pipefail

H="include/data/pokemon/bw3g_generated/bw3g_pokemon_pics.h"
if [[ ! -f "$H" ]]; then
  echo "ERROR: missing $H"
  exit 1
fi

TS="$(date +%Y%m%d_%H%M%S)"
BAK="${H}.bak_u32_${TS}"
cp -a "$H" "$BAK"
echo "Backup created: $BAK"

python3 - <<'PY'
import re, sys

path = "include/data/pokemon/bw3g_generated/bw3g_pokemon_pics.h"
s = open(path, "r", encoding="utf-8", errors="replace").read()
orig = s

# Only change Front/Back pic externs. Keep palettes as u16.
s, n1 = re.subn(r'extern\s+const\s+u8\s+(gMonFrontPic_[A-Za-z0-9_]+Bw3g)\[\]\s*;',
                r'extern const u32 \1[];', s)
s, n2 = re.subn(r'extern\s+const\s+u8\s+(gMonBackPic_[A-Za-z0-9_]+Bw3g)\[\]\s*;',
                r'extern const u32 \1[];', s)

if s == orig:
  print("No changes made (patterns not found).")
  sys.exit(2)

open(path, "w", encoding="utf-8").write(s)
print(f"Patched {path}")
print(f"Replacements: front={n1}, back={n2}")
PY

echo
echo "Sanity check: first 12 pic externs now:"
rg -n 'extern const u(8|32) gMon(Front|Back)Pic_.*Bw3g' "$H" | head -n 12 || true
