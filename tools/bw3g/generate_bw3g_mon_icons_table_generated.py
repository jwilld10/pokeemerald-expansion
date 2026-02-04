#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import re

ROOT = Path(".")
SPECIES_H = ROOT / "include/constants/species_bw3g.h"
OUT_H     = ROOT / "data/graphics/bw3g_mon_icons_table_generated.h"

ICONS_DIR = ROOT / "graphics/bw3g/icons"

# Matches: #define SPECIES_SNIVY_BW3G (SPECIES_ZUBAT_SPACEWORLD + 1)
SPEC_RE = re.compile(r'^\s*#define\s+(SPECIES_[A-Z0-9_]+_BW3G)\s+\(', re.M)

def canon(token: str) -> str:
    s = token.lower()
    s = s.replace("ho_oh", "hooh")
    s = s.replace("mr_mime", "mrmime")
    s = s.replace("mime_jr", "mimejr")
    s = s.replace("porygon_z", "porygonz")
    s = s.replace("nidoran_f", "nidoranf")
    s = s.replace("nidoran_m", "nidoranm")
    return s

def c_ident(name: str) -> str:
    # Make a valid C identifier suffix
    return re.sub(r'[^A-Za-z0-9_]', '_', name)

text = SPECIES_H.read_text(encoding="utf-8", errors="replace")
species = SPEC_RE.findall(text)

if not species:
    raise SystemExit(f"ERROR: no BW3G species parsed from {SPECIES_H}")

# Build a set of available icon basenames
available = {p.stem for p in ICONS_DIR.glob("*.4bpp")}
if not available:
    raise SystemExit(f"ERROR: no *.4bpp icons found under {ICONS_DIR}")

OUT_H.parent.mkdir(parents=True, exist_ok=True)

fallback = "monster" if "monster" in available else next(iter(sorted(available)))

blob_names: list[str] = []
missing: list[str] = []

for full in species:
    # full like SPECIES_SNIVY_BW3G -> token SNIVY
    token = full.removeprefix("SPECIES_").removesuffix("_BW3G")
    base = canon(token)
    stem = base if base in available else fallback
    if base not in available:
        missing.append(base)
    blob_names.append((full, token, stem))

with OUT_H.open("w", encoding="utf-8") as f:
    f.write("// Auto-generated. Do not edit.\n")
    f.write('#ifndef GUARD_BW3G_MON_ICONS_TABLE_GENERATED_H\n')
    f.write('#define GUARD_BW3G_MON_ICONS_TABLE_GENERATED_H\n\n')
    f.write('#include "global.h"\n')
    f.write('#include "graphics.h"\n\n')

    # 1) blobs
    for full, token, stem in blob_names:
        ident = c_ident(token)
        f.write(f'static const u8 sBw3gIcon_{ident}[] = INCBIN_U8("graphics/bw3g/icons/{stem}.4bpp");\n')
    f.write("\n")

    # 2) pointer table
    f.write("static const u8 *const sBw3gMonIconTable[] =\n{\n")
    for full, token, stem in blob_names:
        ident = c_ident(token)
        f.write(f"    sBw3gIcon_{ident}, // {full}\n")
    f.write("};\n\n")

    # Optional: palette table if you later need one; for now palette forced to 7 in pokemon_icon.c
    f.write("#endif // GUARD_BW3G_MON_ICONS_TABLE_GENERATED_H\n")

print(f"Wrote: {OUT_H}")
print(f"Species: {len(species)}")
print(f"Icons available: {len(available)}")
print(f"Missing icons (used fallback '{fallback}.4bpp'): {len(missing)}")
