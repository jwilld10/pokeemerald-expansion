#!/usr/bin/env bash
set -euo pipefail

OUT_H="src/data/pokemon/spaceworld_generated/spaceworld_species_info.h"

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 /path/to/repo1 [/path/to/repo2 ...]" >&2
  exit 2
fi

python3 - "$OUT_H" "$@" <<'PY'
from pathlib import Path
import re
import sys

out_h = Path(sys.argv[1]).resolve()
roots = [Path(p).expanduser().resolve() for p in sys.argv[2:]]

txt = out_h.read_text(encoding="utf-8", errors="ignore")

# --- find SPACEWORLD species blocks & detect missing height/weight ---
start_re = re.compile(r'^\s*\[\s*(SPECIES_[A-Z0-9_]+_SPACEWORLD)\s*\]\s*=\s*$', re.M)
height_re = re.compile(r'^\s*\.height\s*=', re.M)
weight_re = re.compile(r'^\s*\.weight\s*=', re.M)
close_re  = re.compile(r'^\s*\},\s*$', re.M)

starts = [(m.start(), m.end(), m.group(1)) for m in start_re.finditer(txt)]
if not starts:
    raise SystemExit("ERROR: No SPACEWORLD entries found in output header.")

blocks = []
missing_syms = []
for i,(s,e,sym) in enumerate(starts):
    end = starts[i+1][0] if i+1 < len(starts) else len(txt)
    block = txt[e:end]
    miss_h = not bool(height_re.search(block))
    miss_w = not bool(weight_re.search(block))
    blocks.append((s,e,end,sym,miss_h,miss_w))
    if miss_h or miss_w:
        missing_syms.append(sym)

def norm(s: str) -> str:
    return s.upper()

missing_mons = [sym.replace("SPECIES_","").replace("_SPACEWORLD","") for sym in missing_syms]
missing_set = set(map(norm, missing_mons))

print(f"Output file: {out_h}")
print(f"Total species blocks: {len(starts)}")
print(f"Missing height/weight at start: {len(missing_syms)}")
print()

# --- heuristics: convert label/filename into MON_KEY like MR_MIME, HO_OH ---
camel_boundary = re.compile(r'(?<!^)(?=[A-Z])')

def camel_to_snake(s: str) -> str:
    # MrMime -> MR_MIME ; HoOh -> HO_OH ; NidoranF -> NIDORAN_F
    # Also handle things like FarfetchD -> FARFETCH_D
    parts = camel_boundary.split(s)
    return norm("_".join(parts))

def stem_to_key(stem: str) -> str:
    # mr_mime -> MR_MIME, ho_oh -> HO_OH
    return norm(stem)

# common label patterns in pokecrystal-ish repos
label_re = re.compile(r'^\s*([A-Za-z0-9_]+)\s*PokedexEntry::', re.M)

# strict: "dw H, W ; height, weight"
hw_strict = re.compile(r'^\s*dw\s+([0-9]+)\s*,\s*([0-9]+)\s*;\s*height\s*,\s*weight\b', re.M)

# fallback: within ~5 lines after a db "NAME@" line, find dw H, W
db_name = re.compile(r'^\s*db\s+"[^"]*@".*$', re.M)
dw_hw_loose = re.compile(r'^\s*dw\s+([0-9]+)\s*,\s*([0-9]+)\s*(?:;.*)?$', re.M)

def extract_hw_from_text(t: str):
    m = hw_strict.search(t)
    if m:
        return int(m.group(1)), int(m.group(2))

    # fallback window scan
    lines = t.splitlines()
    for i,line in enumerate(lines):
        if db_name.match(line):
            for j in range(i+1, min(i+6, len(lines))):
                m2 = dw_hw_loose.match(lines[j])
                if m2:
                    return int(m2.group(1)), int(m2.group(2))
    return None

repo_maps = []
for root in roots:
    if not root.is_dir():
        print(f"SKIP (not a dir): {root}")
        continue

    asm_files = list(root.rglob("*.asm"))
    if not asm_files:
        print(f"SKIP (no .asm): {root}")
        continue

    mp = {}
    for f in asm_files:
        try:
            t = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        hw = extract_hw_from_text(t)
        if not hw:
            continue
        h,w = hw

        # Prefer label; but normalize label via CamelCase -> snake
        lab = label_re.search(t)
        if lab:
            raw = lab.group(1)
            key = camel_to_snake(raw)
        else:
            key = stem_to_key(f.stem)

        mp.setdefault(key, (h,w))

    repo_maps.append((root, mp))
    print(f"Scanned {len(asm_files)} asm files; found {len(mp)} height/weight candidates in {root}")

if not repo_maps:
    raise SystemExit("ERROR: None of the provided repos yielded any height/weight candidates.")

print()

def find_hw(mon_key: str):
    # direct
    for root, mp in repo_maps:
        if mon_key in mp:
            return root, mp[mon_key]

    # underscore-less variant
    v = mon_key.replace("_","")
    for root, mp in repo_maps:
        if v in mp:
            return root, mp[v]

    # contained unique match
    for root, mp in repo_maps:
        hits = [k for k in mp.keys() if mon_key in k or k in mon_key]
        if len(hits) == 1:
            return root, mp[hits[0]]

    return None, None

patched = 0
still_missing = []

for s,e,end,sym,miss_h,miss_w in reversed(blocks):
    if not (miss_h or miss_w):
        continue

    mon = sym.replace("SPECIES_","").replace("_SPACEWORLD","")
    mon_key = norm(mon)

    root, hw = find_hw(mon_key)
    if hw is None:
        still_missing.append(sym)
        continue

    h,w = hw

    block = txt[e:end]
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
