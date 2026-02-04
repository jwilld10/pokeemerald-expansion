#!/usr/bin/env bash
set -euo pipefail

IN="src/data/pokemon/spaceworld_generated/spaceworld_species_info.h"
OUT="tools/spaceworld/approx_hw_manifest.txt"

[[ -f "$IN" ]] || { echo "ERROR: missing $IN" >&2; exit 1; }

mkdir -p "$(dirname "$OUT")"

python3 - <<'PY'
from pathlib import Path
import re
from datetime import datetime

inp = Path("src/data/pokemon/spaceworld_generated/spaceworld_species_info.h")
outp = Path("tools/spaceworld/approx_hw_manifest.txt")

txt = inp.read_text(encoding="utf-8", errors="ignore")

# block header like: [SPECIES_ABRA_SPACEWORLD] =
start_re = re.compile(r'^\s*\[\s*(SPECIES_[A-Z0-9_]+_SPACEWORLD)\s*\]\s*=\s*', re.M)
starts = [(m.start(), m.end(), m.group(1)) for m in start_re.finditer(txt)]

def find_block_end(i):
    if i + 1 < len(starts):
        return starts[i+1][0]
    return len(txt)

height_re = re.compile(r'^\s*\.height\s*=\s*(\d+)\s*,\s*(//.*)?$', re.M)
weight_re = re.compile(r'^\s*\.weight\s*=\s*(\d+)\s*,\s*(//.*)?$', re.M)

rows = []
for i,(s,e,sym) in enumerate(starts):
    block = txt[e:find_block_end(i)]
    hm = height_re.search(block)
    wm = weight_re.search(block)
    if not hm or not wm:
        continue

    h_val = int(hm.group(1))
    w_val = int(wm.group(1))
    h_cmt = hm.group(2) or ""
    w_cmt = wm.group(2) or ""
    h_approx = "approx from sprite bbox" in h_cmt
    w_approx = "approx from sprite bbox" in w_cmt

    # We only list ones that are approximated (either height or weight line marked)
    if h_approx or w_approx:
        rows.append((sym, h_val, w_val, h_approx, w_approx))

rows.sort(key=lambda r: r[0])

header = []
header.append("SPACEWORLD approx height/weight manifest")
header.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
header.append(f"Input: {inp}")
header.append(f"Approx-count: {len(rows)}")
header.append("")
header.append("Format:")
header.append("  SPECIES_SYMBOL  height  weight  (H approx?) (W approx?)")
header.append("")

lines = header[:]
for sym,h,w,ha,wa in rows:
    lines.append(f"{sym:<32} {h:>5} {w:>6}   H={'Y' if ha else 'N'}  W={'Y' if wa else 'N'}")

outp.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"Wrote: {outp}  (rows={len(rows)})")
PY
