#!/usr/bin/env bash
set -euo pipefail
cd ~/decomps/pokeemerald-expansion_clean

OUT="tools/bw3g/_givemon_trunc_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUT"

echo "Writing to: $OUT"

# 1) Find ScriptGiveMon declaration/definition + any prototypes
{
  echo "=== ScriptGiveMon hits (declaration/definition/calls) ==="
  rg -n --no-heading '\bScriptGiveMon\b' src include | head -n 200
  echo
} > "$OUT/01_scriptgivemon_hits.txt"

# 2) Try to capture the function signature and body (best-effort)
python3 - <<'PY' > "$OUT/02_scriptgivemon_signature_and_body.txt"
import re, glob

def read(p):
    try:
        return open(p,'r',encoding='utf-8',errors='replace').read()
    except:
        return ""

paths = glob.glob("src/**/*.c", recursive=True) + glob.glob("include/**/*.h", recursive=True)
for p in paths:
    s = read(p)
    if "ScriptGiveMon" not in s:
        continue
    # Grab signatures like: ScriptGiveMon( ... ) { ... }
    m = re.search(r'(\bScriptGiveMon\s*\([^;{]*\)\s*\{.*?\n\})', s, flags=re.S)
    if m:
        print(f"--- {p} ---")
        print(m.group(1)[:4000])
        print()
PY

# 3) Find script command that actually gives a mon (commonly ScrCmd_givemon / ScrCmd_givepokemon)
{
  echo "=== Likely script give-mon command(s) ==="
  rg -n --no-heading 'ScrCmd_.*give(mon|pokemon)|\bgive(mon|pokemon)\b' src | head -n 200
  echo
} > "$OUT/03_scrc_givemon_hits.txt"

# 4) Find any suspicious u8 usage on species inside these paths
{
  echo "=== Suspicious: u8 species in give-mon related code ==="
  rg -n --no-heading 'u8\s+species\b|\(u8\)\s*species|\(u8\)\s*sDebugMonData->species' src include | head -n 200
  echo
} > "$OUT/04_suspicious_u8_species_hits.txt"

# 5) OPTIONAL AUTO-PATCH:
# If we can find a ScriptGiveMon signature that takes u8 species, patch it to u16.
# (This does NOT run unless PATCH=1 is set.)
if [[ "${PATCH:-0}" == "1" ]]; then
  echo "PATCH=1 set; attempting safe signature patch..."

  # Make a backup of any file that contains "u8 species" in ScriptGiveMon signature
  python3 - <<'PY'
import re, glob, os, shutil, time

def read(p):
    return open(p,'r',encoding='utf-8',errors='replace').read()

def write(p, s):
    open(p,'w',encoding='utf-8').write(s)

ts = time.strftime("%Y%m%d_%H%M%S")
changed = 0

for p in glob.glob("src/**/*.c", recursive=True):
    s = read(p)
    # patch only if signature has "ScriptGiveMon" and "(u8 species" or ", u8 species"
    if "ScriptGiveMon" not in s:
        continue

    # conservative: patch "ScriptGiveMon(u8 species," and "ScriptGiveMon(u8 species)" etc
    s2, n = re.subn(r'(\bScriptGiveMon\s*\()\s*u8(\s+species\b)', r'\1u16\2', s)
    if n:
        bak = f"{p}.bak_givemon_{ts}"
        shutil.copy2(p, bak)
        write(p, s2)
        print(f"Patched {p} (backup {bak}) changes={n}")
        changed += n

print("TOTAL changes:", changed)
PY
fi

echo "DONE. Files written under: $OUT"
ls -ლა "$OUT" > "$OUT/ls.txt"
