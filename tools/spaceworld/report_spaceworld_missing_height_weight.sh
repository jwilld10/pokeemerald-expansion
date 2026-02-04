#!/usr/bin/env bash
set -euo pipefail

OUT_H="src/data/pokemon/spaceworld_generated/spaceworld_species_info.h"

python3 - "$OUT_H" <<'PY'
from pathlib import Path
import re
import sys

out_h = Path(sys.argv[1])
txt = out_h.read_text(encoding="utf-8", errors="ignore")

start_re = re.compile(r'^\s*\[\s*(SPECIES_[A-Z0-9_]+_SPACEWORLD)\s*\]\s*=\s*$', re.M)
height_re = re.compile(r'^\s*\.height\s*=', re.M)
weight_re = re.compile(r'^\s*\.weight\s*=', re.M)

starts = [(m.start(), m.end(), m.group(1)) for m in start_re.finditer(txt)]
missing = []

for i,(s,e,sym) in enumerate(starts):
    end = starts[i+1][0] if i+1 < len(starts) else len(txt)
    block = txt[e:end]
    if not height_re.search(block) or not weight_re.search(block):
        missing.append(sym)

print(f"Total species blocks: {len(starts)}")
print(f"Missing height/weight: {len(missing)}")
for sym in missing:
    print(sym)
PY
