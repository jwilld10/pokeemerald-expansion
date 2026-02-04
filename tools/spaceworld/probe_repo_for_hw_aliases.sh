#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:?usage: $0 /path/to/repo}"
ROOT="$(realpath "$ROOT")"

# alias list: SPACEWORLD name -> likely name in old repos
# (these are the ones you said are missing hw)
declare -A ALIAS=(
  [BELLRUN]=BELLEDAM
  [BELMITT]=BELLIGNAN
  [BOMSHEAL]=GRENMAR
  [CORASUN]=MOLAMBINO
  [CRUIZE]=PALSSIO
  [ELEBABE]=ELEKID
  [GELANIA]=JUNGELA
  [GUPGOLD]=ORFRY
  [KURSTRAW]=STROMEN
  [METTO]=MIMMEO
  [NYANYA]=COINPUR
  [PANGSHI]=PHANDARIN
  [PARAMITE]=PARASPOR
  [PETAMOLE]=BLOSSOMOLE
  [PETICORN]=KOLTA
  [PRAXE]=TRICULES
  [PUDDIPUP]=PUPPERON
  [TANGTRIP]=BURGELA
  [TRIPSTAR]=LEDIAN
)

echo "ROOT: $ROOT"
echo

python3 - "$ROOT" <<'PY'
import re, sys, subprocess
from pathlib import Path

root = Path(sys.argv[1])

# must match bash ALIAS dict above (duplicated here to keep script self-contained)
ALIASES = {
  "BELLRUN":"BELLEDAM",
  "BELMITT":"BELLIGNAN",
  "BOMSHEAL":"GRENMAR",
  "CORASUN":"MOLAMBINO",
  "CRUIZE":"PALSSIO",
  "ELEBABE":"ELEKID",
  "GELANIA":"JUNGELA",
  "GUPGOLD":"ORFRY",
  "KURSTRAW":"STROMEN",
  "METTO":"MIMMEO",
  "NYANYA":"COINPUR",
  "PANGSHI":"PHANDARIN",
  "PARAMITE":"PARASPOR",
  "PETAMOLE":"BLOSSOMOLE",
  "PETICORN":"KOLTA",
  "PRAXE":"TRICULES",
  "PUDDIPUP":"PUPPERON",
  "TANGTRIP":"BURGELA",
  "TRIPSTAR":"LEDIAN",
}

def rg(pattern, extra=None, maxlines=20):
    cmd = ["rg","-n","--hidden","--no-ignore-vcs","-S"]
    if extra: cmd += extra
    cmd += [pattern, str(root)]
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, text=True)
    except subprocess.CalledProcessError:
        return []
    lines = out.splitlines()
    return lines[:maxlines]

def find_dex_files():
    # common candidates across these repos
    cands = []
    for p in [
        root/"data/pokemon/dex_entries.asm",
        root/"data/pokemon/dex_entries_gold.asm",
        root/"data/pokemon/dex_entries/dex_entries.asm",
    ]:
        if p.exists():
            cands.append(p)
    # plus any dex_entries*.asm
    cands += list(root.rglob("dex_entries*.asm"))
    # de-dupe
    seen = set()
    out = []
    for p in cands:
        rp = str(p.resolve())
        if rp not in seen:
            seen.add(rp)
            out.append(p)
    return out

dex_files = find_dex_files()

label_re = re.compile(r'^\s*([A-Za-z0-9_]+)\s*:\s*$')
db_num  = re.compile(r'^\s*db\s+([0-9]+)\b', re.I)
dw_num  = re.compile(r'^\s*dw\s+([0-9]+)\b', re.I)
dw_pair = re.compile(r'^\s*dw\s+([0-9]+)\s*,\s*([0-9]+)\b', re.I)  # BW3G-style

def try_extract_hw_near_label(dex_text_lines, label):
    # return (h,w,format) if found
    idx = None
    for i,l in enumerate(dex_text_lines):
        m = label_re.match(l)
        if m and m.group(1) == label:
            idx = i
            break
    if idx is None:
        return None

    h = None
    w = None

    # Scan the next ~20 lines for known formats
    for j in range(idx+1, min(idx+25, len(dex_text_lines))):
        line = dex_text_lines[j]

        # BW3G-ish: dw height, weight
        m = dw_pair.match(line)
        if m:
            return (int(m.group(1)), int(m.group(2)), "dw height, weight")

        # pokegold-spaceworld-ish: db height; dw weight
        if h is None:
            m = db_num.match(line)
            if m:
                h = int(m.group(1))
                continue
        if h is not None and w is None:
            m = dw_num.match(line)
            if m:
                w = int(m.group(1))
                return (h, w, "db height; dw weight")

    return None

print(f"Dex files detected: {len(dex_files)}")
for p in dex_files[:10]:
    print("  -", p)
if len(dex_files) > 10:
    print("  ...")
print()

for sw, alias in sorted(ALIASES.items()):
    print(f"== {sw} (alias: {alias}) ==")

    # 1) DEX constant usage (very telling)
    dex_const_hits = rg(rf"\bDEX_{re.escape(alias)}\b")
    print("DEX_ const hits:", "yes" if dex_const_hits else "no")
    if dex_const_hits:
        print("  sample:", dex_const_hits[0])

    # 2) base_stats file name hit
    bs_hits = rg(rf"data/pokemon/base_stats/.*{re.escape(alias.lower())}", extra=["-i"], maxlines=5)
    print("base_stats filename-ish hit:", "yes" if bs_hits else "no")
    if bs_hits:
        for line in bs_hits:
            print(" ", line)

    # 3) DexEntry label hits (search whole repo)
    label_pat = rf"\b{re.escape(alias.title().replace('_',''))}DexEntry\b|\b{re.escape(alias.capitalize())}DexEntry\b|\b{re.escape(alias)}DexEntry\b"
    label_hits = rg(label_pat, maxlines=10)
    print("DexEntry label mention:", "yes" if label_hits else "no")
    if label_hits:
        for line in label_hits[:3]:
            print(" ", line)

    # 4) If we found a label mention, attempt to extract hw from actual dex files
    extracted_any = False
    for dex in dex_files:
        try:
            lines = dex.read_text(encoding="utf-8", errors="ignore").splitlines()
        except Exception:
            continue

        # find exact label name(s) inside this dex file
        candidate_labels = []
        for l in lines:
            m = label_re.match(l)
            if not m:
                continue
            lbl = m.group(1)
            # accept if alias is substring (case-insensitive) or common DexEntry naming
            if alias.replace("_","").lower() in lbl.replace("_","").lower():
                candidate_labels.append(lbl)

        for lbl in candidate_labels[:6]:
            hw = try_extract_hw_near_label(lines, lbl)
            if hw:
                h,w,fmt = hw
                print(f"EXTRACTED from {dex}: label={lbl}  height={h}  weight={w}  ({fmt})")
                extracted_any = True
                break
        if extracted_any:
            break

    if not extracted_any:
        print("EXTRACTED:", "no")
    print()
PY
