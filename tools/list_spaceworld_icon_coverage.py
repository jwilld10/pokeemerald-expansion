#!/usr/bin/env python3
from pathlib import Path
import re

H = Path("src/data/pokemon/spaceworld_generated/spaceworld_species_info.h")
GFX_H = Path("include/graphics.h")

if not H.exists():
    raise SystemExit(f"Missing: {H}")
if not GFX_H.exists():
    raise SystemExit(f"Missing: {GFX_H}")

# 1) Which gSwIcon_* are used by species info?
src = H.read_text(encoding="utf-8", errors="ignore")
used = sorted(set(re.findall(r'\.\s*iconSprite\s*=\s*(gSwIcon_[A-Za-z0-9_]+)', src)))

# 2) Which gSwIcon_* are declared in graphics.h (and what file they point to, if it’s written inline)?
gfx = GFX_H.read_text(encoding="utf-8", errors="ignore").splitlines()

decl = set()
paths = {}  # symbol -> string path if we can infer it from include/graphics.h patterns

# Common patterns in pokeemerald-expansion:
# extern const u8 gSwIcon_BatTiles[];  or gSwIcon_Bat[] etc.
sym_re = re.compile(r'\b(gSwIcon_[A-Za-z0-9_]+)\b')
incbin_re = re.compile(r'INCBIN.*\(\s*"([^"]+)"\s*\)')

last_syms = []
for line in gfx:
    syms = sym_re.findall(line)
    if syms:
        for s in syms:
            decl.add(s)
        last_syms = syms[:]  # for pairing with an incbin line if it appears next
    m = incbin_re.search(line)
    if m and last_syms:
        p = m.group(1)
        for s in last_syms:
            paths.setdefault(s, p)

print(f"[spaceworld_species_info] gSwIcon_* used: {len(used)}")
print(f"[graphics.h] gSwIcon_* declared: {len(decl)}")
print()

missing_decl = [s for s in used if s not in decl]
print(f"Used in species info but NOT declared in graphics.h: {len(missing_decl)}")
for s in missing_decl[:50]:
    print("  ", s)
if len(missing_decl) > 50:
    print("  ...")

print()
print("Used icons (and known paths if detectable):")
for s in used:
    p = paths.get(s)
    if p:
        print(f"  {s:28} -> {p}")
    else:
        print(f"  {s:28} -> (path not inferred)")

