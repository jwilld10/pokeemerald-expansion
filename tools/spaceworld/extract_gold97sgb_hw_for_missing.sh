#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:?usage: $0 /path/to/Gold97SGB}"
ROOT="$(realpath "$ROOT")"

DEX="$ROOT/data/pokemon/dex_entries_gold.asm"
[[ -f "$DEX" ]] || { echo "ERROR: missing $DEX" >&2; exit 1; }

python3 - "$DEX" <<'PY'
import re, sys
from pathlib import Path

dex = Path(sys.argv[1]).read_text(encoding="utf-8", errors="ignore").splitlines()

# SPACEWORLD -> Gold97SGB alias (what you just gave)
ALIASES = {
  "BELLRUN":  ["BELLEDAM"],
  "BELMITT":  ["BELLIGNAN"],
  "BOMSHEAL": ["GRENMAR"],
  "CORASUN":  ["MOLAMBINO"],
  "CRUIZE":   ["PALSSIO"],
  "ELEBABE":  ["ELEKID"],
  "GELANIA":  ["JUNGELA"],
  "GUPGOLD":  ["ORFRY"],
  "KURSTRAW": ["STROMEN"],
  "METTO":    ["MIMMEO"],
  "NYANYA":   ["COINPUR"],
  "PANGSHI":  ["PHANDARIN"],
  "PARAMITE": ["PARASPOR"],
  "PETAMOLE": ["BLOSSOMOLE"],
  "PETICORN": ["KOLTA"],
  "PRAXE":    ["TRICULES"],
  "PUDDIPUP": ["PUPPERON"],
  "TANGTRIP": ["BURGELA"],
  "TRIPSTAR": ["LEDIAN"],
}

label_re = re.compile(r'^\s*([A-Za-z0-9_]+)\s*:\s*$')
db_re    = re.compile(r'^\s*db\s+([0-9]+)\b', re.I)
dw_re    = re.compile(r'^\s*dw\s+([0-9]+)\b', re.I)

# index labels -> line#
labels = {}
for i, line in enumerate(dex):
    m = label_re.match(line)
    if m:
        labels[m.group(1)] = i

def find_hw_after(label):
    """Read db height then dw weight within next ~10 lines."""
    if label not in labels:
        return None
    i = labels[label]
    height = None
    weight = None
    for j in range(i+1, min(i+15, len(dex))):
        if height is None:
            m = db_re.match(dex[j])
            if m:
                height = int(m.group(1))
                continue
        if height is not None and weight is None:
            m = dw_re.match(dex[j])
            if m:
                weight = int(m.group(1))
                break
    if height is None or weight is None:
        return None
    return height, weight

print(f"DEX: {sys.argv[1]}")
print()

missing = []
for sw, als in sorted(ALIASES.items()):
    # typical label naming in these repos is <Name>DexEntry
    # We try both TitleCase and UPPER-ish just in case.
    found = None
    tried = []
    for a in als:
        # e.g. COINPUR -> CoinpurDexEntry
        label1 = a.capitalize().lower().capitalize()  # quick-ish, not perfect
        # better: TitleCase by splitting underscores
        parts = a.split("_")
        label2 = "".join(p[:1] + p[1:].lower() for p in parts)  # COINPUR -> Coinpur
        for base in {label1, label2, a.title().replace("_","")}:
            lbl = f"{base}DexEntry"
            tried.append(lbl)
            hw = find_hw_after(lbl)
            if hw:
                found = (a, lbl, hw[0], hw[1])
                break
        if found:
            break

    if not found:
        missing.append((sw, als, tried[:6]))
        continue

    a, lbl, h, w = found
    print(f"{sw:10} <= {a:12}  {lbl:22}  height={h}  weight={w}")

print()
if missing:
    print("Could not extract hw for:")
    for sw, als, t in missing:
        print(f"  {sw:10} aliases={als} tried_labels~={t}")
else:
    print("Extracted hw for all aliases.")
PY
