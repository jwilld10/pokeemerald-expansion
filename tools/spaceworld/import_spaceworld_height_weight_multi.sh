#!/usr/bin/env bash
set -euo pipefail

OUT_H="src/data/pokemon/spaceworld_generated/spaceworld_species_info.h"

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 /path/to/repo1 [/path/to/repo2 ...]" >&2
  echo "Example: $0 ~/decomps/gold97 ~/decomps/Gold97SGB ~/decomps/pokegold-spaceworld" >&2
  exit 2
fi

python3 - "$OUT_H" "$@" <<'PY'
from pathlib import Path
import re
import sys

out_h = Path(sys.argv[1])
roots = [Path(p).expanduser().resolve() for p in sys.argv[2:]]

txt = out_h.read_text(encoding="utf-8", errors="ignore")

# --- find SPACEWORLD species blocks & detect which miss height/weight ---
start_re = re.compile(r'^\s*\[\s*(SPECIES_[A-Z0-9_]+_SPACEWORLD)\s*\]\s*=\s*$', re.M)
height_re = re.compile(r'^\s*\.height\s*=', re.M)
weight_re = re.compile(r'^\s*\.weight\s*=', re.M)
close_re  = re.compile(r'^\s*\},\s*$', re.M)

starts = [(m.start(), m.end(), m.group(1)) for m in start_re.finditer(txt)]
if not starts:
  raise SystemExit("ERROR: No SPACEWORLD entries found in output header.")

missing_syms = []
blocks = []
for i,(s,e,sym) in enumerate(starts):
    end = starts[i+1][0] if i+1 < len(starts) else len(txt)
    block = txt[e:end]
    miss_h = not bool(height_re.search(block))
    miss_w = not bool(weight_re.search(block))
    blocks.append((s,e,end,sym,miss_h,miss_w))
    if miss_h or miss_w:
        missing_syms.append(sym)

print(f"Output file: {out_h}")
print(f"Total species blocks: {len(starts)}")
print(f"Missing height/weight at start: {len(missing_syms)}")
print()

# --- parse dex repos into (MONNAME -> (height, weight)) maps ---
include_re = re.compile(r'^\s*([A-Za-z0-9_]+)PokedexEntry::\s+INCLUDE\s+"data/pokemon/dex_entries/([^"]+\.asm)"', re.M)
hw_re = re.compile(r'^\s*dw\s+([0-9]+)\s*,\s*([0-9]+)\s*;\s*height\s*,\s*weight', re.M)

def normalize_mon(name: str) -> str:
    # Convert SPECIES_FOO_SPACEWORLD -> FOO
    name = name.upper()
    name = name.replace("’","'")  # just in case
    return name

repo_maps = []
for root in roots:
    dex_main = root / "data/pokemon/dex_entries.asm"
    dex_dir  = root / "data/pokemon/dex_entries"
    if not dex_main.is_file() or not dex_dir.is_dir():
        print(f"SKIP (no dex): {root}")
        continue

    dex_txt = dex_main.read_text(encoding="utf-8", errors="ignore")
    pairs = include_re.findall(dex_txt)
    m = {}
    for mon, rel in pairs:
        f = root / "data/pokemon/dex_entries" / rel
        if not f.is_file():
            continue
        t = f.read_text(encoding="utf-8", errors="ignore")
        mhw = hw_re.search(t)
        if not mhw:
            continue
        h = int(mhw.group(1))
        w = int(mhw.group(2))
        m[normalize_mon(mon)] = (h, w)

    repo_maps.append((root, m))
    print(f"Loaded {len(m)} height/weight entries from {root}")

if not repo_maps:
    raise SystemExit("ERROR: None of the provided repos contained dex_entries.asm + dex_entries/")

print()

# --- patch OUT_H for missing entries, trying repos in order ---
patched = 0
still_missing = []

# Work backwards so string slicing stays valid
for s,e,end,sym,miss_h,miss_w in reversed(blocks):
    if not (miss_h or miss_w):
        continue

    mon = sym.replace("SPECIES_","").replace("_SPACEWORLD","")
    mon_norm = normalize_mon(mon)

    found = None
    found_in = None
    for root, mp in repo_maps:
        if mon_norm in mp:
            found = mp[mon_norm]
            found_in = root
            break

    if not found:
        still_missing.append(sym)
        continue

    h, w = found

    block = txt[e:end]
    # If the file already has one of them, only insert the missing one(s)
    add_lines = []
    if miss_h:
        add_lines.append(f"        .height = {h},")
    if miss_w:
        add_lines.append(f"        .weight = {w},")
    ins = "\n".join(add_lines) + "\n"

    mclose = close_re.search(block)
    if not mclose:
        still_missing.append(sym)
        continue

    insert_at = mclose.start()
    block2 = block[:insert_at] + ins + block[insert_at:]

    txt = txt[:e] + block2 + txt[end:]
    patched += 1
    # (optional) print each patch
    # print(f"Patched {sym} from {found_in} -> height={h} weight={w}")

out_h.write_text(txt, encoding="utf-8")

print("----")
print(f"Patched blocks: {patched}")
print(f"Still missing after patch: {len(still_missing)}")
if still_missing:
    for sym in sorted(still_missing):
        print(sym)
print()
print(f"Wrote: {out_h}")
PY
