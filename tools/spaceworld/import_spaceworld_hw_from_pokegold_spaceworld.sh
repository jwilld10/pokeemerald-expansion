#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:?usage: $0 /path/to/pokegold-spaceworld}"
ROOT="$(realpath "$ROOT")"

DEX="$ROOT/data/pokemon/dex_entries.asm"
OUT_H="src/data/pokemon/spaceworld_generated/spaceworld_species_info.h"

[[ -f "$DEX"   ]] || { echo "ERROR: missing $DEX" >&2; exit 1; }
[[ -f "$OUT_H" ]] || { echo "ERROR: missing $OUT_H" >&2; exit 1; }

DEX_PATH="$DEX" OUT_PATH="$OUT_H" python3 - <<'PY'
from pathlib import Path
import os, re, sys

dex_path = Path(os.environ["DEX_PATH"])
out_path = Path(os.environ["OUT_PATH"])

dex = dex_path.read_text(encoding="utf-8", errors="ignore").splitlines()
txt = out_path.read_text(encoding="utf-8", errors="ignore")

# ------------- helpers -------------
def norm(s: str) -> str:
    # aggressive normalization: remove non-alnum, lowercase
    return re.sub(r'[^a-z0-9]', '', s.lower())

# Parse all labels that look like "<Name>DexEntry:"
label_re = re.compile(r'^\s*([A-Za-z0-9_]+)DexEntry:\s*$')

# In pokegold-spaceworld format:
#   db "CATEGORY@"
#   db <height>
#   dw <weight>
db_str_re = re.compile(r'^\s*db\s+"[^"]*"\s*$')
db_num_re = re.compile(r'^\s*db\s+([0-9]+|\$[0-9A-Fa-f]+)\s*(?:;.*)?$')
dw_num_re = re.compile(r'^\s*dw\s+([0-9]+|\$[0-9A-Fa-f]+)\s*(?:;.*)?$')

def parse_num(tok: str) -> int:
    tok = tok.strip()
    if tok.startswith("$"):
        return int(tok[1:], 16)
    return int(tok, 10)

# Build mapping from normalized label-name -> (height, weight)
dex_hw = {}  # norm(name) -> (height, weight)
i = 0
while i < len(dex):
    m = label_re.match(dex[i])
    if not m:
        i += 1
        continue

    name = m.group(1)  # e.g. "NidoranF", "Farfetchd", "MrMime"
    # look ahead for the 3 lines that define category/height/weight
    j = i + 1

    # Skip blank/comment lines
    while j < len(dex) and (dex[j].strip() == "" or dex[j].lstrip().startswith(";")):
        j += 1

    if j >= len(dex) or not db_str_re.match(dex[j]):
        i += 1
        continue
    j += 1

    # height line
    while j < len(dex) and (dex[j].strip() == "" or dex[j].lstrip().startswith(";")):
        j += 1
    if j >= len(dex):
        i += 1
        continue
    mh = db_num_re.match(dex[j])
    if not mh:
        i += 1
        continue
    height = parse_num(mh.group(1))
    j += 1

    # weight line
    while j < len(dex) and (dex[j].strip() == "" or dex[j].lstrip().startswith(";")):
        j += 1
    if j >= len(dex):
        i += 1
        continue
    mw = dw_num_re.match(dex[j])
    if not mw:
        i += 1
        continue
    weight = parse_num(mw.group(1))

    dex_hw[norm(name)] = (height, weight)
    i += 1

print(f"Loaded height/weight from: {dex_path}")
print(f"Parsed dex entries with hw: {len(dex_hw)}")

# ----------- patch OUT_H -----------
# Species block starts in your spaceworld file are like:
#   [SPECIES_FOO_SPACEWORLD] =
# We patch inside the {...} block before the closing "},".

start_re = re.compile(r'^\s*\[\s*(SPECIES_[A-Z0-9_]+_SPACEWORLD)\s*\]\s*=\s*$', re.M)

starts = [(m.start(), m.end(), m.group(1)) for m in start_re.finditer(txt)]
seen = {}
for s, e, sy in starts:
    seen.setdefault(sy, (s, e, sy))
starts = sorted(seen.values(), key=lambda t: t[0])

height_re = re.compile(r'^\s*\.height\s*=', re.M)
weight_re = re.compile(r'^\s*\.weight\s*=', re.M)

def species_to_key(species_sym: str) -> str:
    # SPECIES_MR_MIME_SPACEWORLD -> MR_MIME
    core = species_sym
    core = core.removeprefix("SPECIES_").removesuffix("_SPACEWORLD")
    return core

patched = 0
still_missing = []

out_parts = []
cursor = 0

for idx, (s, e, sy) in enumerate(starts):
    block_end = starts[idx + 1][0] if idx + 1 < len(starts) else len(txt)
    header = txt[cursor:e]
    block = txt[e:block_end]
    cursor = block_end

    has_h = bool(height_re.search(block))
    has_w = bool(weight_re.search(block))

    if has_h and has_w:
        out_parts.append(header)
        out_parts.append(block)
        continue

    # Find matching dex entry via normalized key
    key = species_to_key(sy)

    # Try a few normalizations for common weird names
    candidates = [
        key,                          # MR_MIME
        key.replace("_", ""),         # MRMIME
        key.replace("_", " "),        # MR MIME
    ]

    hw = None
    for cand in candidates:
        hw = dex_hw.get(norm(cand))
        if hw:
            break

    if not hw:
        # also try title-cased join version: MR_MIME -> MrMime, FARFETCH_D -> FarfetchD
        join = "".join([p[:1] + p[1:].lower() for p in key.split("_") if p])
        hw = dex_hw.get(norm(join))

    if not hw:
        still_missing.append(sy)
        out_parts.append(header)
        out_parts.append(block)
        continue

    h, w = hw

    # Insert before the first line that starts with "}," (close of this species struct)
    mclose = re.search(r'^\s*\},\s*$', block, flags=re.M)
    if not mclose:
        still_missing.append(sy)
        out_parts.append(header)
        out_parts.append(block)
        continue

    insert_pos = mclose.start()
    before = block[:insert_pos]
    close_and_after = block[insert_pos:]

    # choose indentation based on existing style: use 8 spaces if we see "        ."
    indent = "        " if re.search(r'^\s{8}\.\w+', before, flags=re.M) else "    "

    insert_lines = ""
    if not has_h:
        insert_lines += f"{indent}.height = {h},\n"
    if not has_w:
        insert_lines += f"{indent}.weight = {w},\n"

    new_block = before + insert_lines + close_and_after
    out_parts.append(header)
    out_parts.append(new_block)
    patched += 1

new_txt = "".join(out_parts)

out_path.write_text(new_txt, encoding="utf-8")

print("----")
print(f"Patched blocks: {patched}")
print(f"Still missing after patch: {len(still_missing)}")
for s in still_missing[:50]:
    print(s)
if len(still_missing) > 50:
    print(f"(showing first 50 of {len(still_missing)})")
print(f"Wrote: {out_path}")
PY

