#!/usr/bin/env bash
set -euo pipefail

C="src/bw3g_pokemon_pics.c"
if [[ ! -f "$C" ]]; then
  echo "ERROR: missing $C"
  exit 1
fi

TS="$(date +%Y%m%d_%H%M%S)"
BAK="${C}.bak_u32_${TS}"
cp -a "$C" "$BAK"
echo "Backup created: $BAK"

python3 - <<'PY'
import re, sys

path = "src/bw3g_pokemon_pics.c"
s = open(path, "r", encoding="utf-8", errors="replace").read()
orig = s

# 1) Change INCBIN_U8("...smol") -> INCBIN_U32("...smol")
s, n1 = re.subn(r'INCBIN_U8\("([^"]+\.smol)"\)', r'INCBIN_U32("\1")', s)

# 2) Change `const u8 gMonFrontPic_...[] =` -> `const u32 gMonFrontPic_...[] =`
s, n2 = re.subn(r'ALIGNED\(4\)\s+const\s+u8\s+(gMon(?:Front|Back)Pic_[A-Za-z0-9_]+)\[\]\s*=\s*INCBIN_U32',
                r'ALIGNED(4) const u32 \1[] = INCBIN_U32', s)

# If some lines are `const u8` without ALIGNED macro, handle too:
s, n3 = re.subn(r'\bconst\s+u8\s+(gMon(?:Front|Back)Pic_[A-Za-z0-9_]+)\[\]\s*=\s*INCBIN_U32',
                r'const u32 \1[] = INCBIN_U32', s)

if s == orig:
  print("No changes made (patterns not found).")
  sys.exit(2)

open(path, "w", encoding="utf-8").write(s)
print(f"Patched {path}")
print(f"Replacements:")
print(f"  INCBIN_U8(smol)->INCBIN_U32(smol): {n1}")
print(f"  const u8 Front/Back -> const u32 (ALIGNED form): {n2}")
print(f"  const u8 Front/Back -> const u32 (non-ALIGNED form): {n3}")
PY

echo
echo "Quick sanity sample (first 10 front pic defs):"
rg -n 'gMonFrontPic_.*Bw3g' "$C" | head -n 10 || true
