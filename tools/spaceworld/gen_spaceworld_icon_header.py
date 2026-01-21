#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path

SRC_DIR = Path("graphics/spaceworld/icons")
OUT_H   = Path("src/data/graphics/spaceworld_icons.h")

def camel(name: str) -> str:
    parts = [p for p in name.split("_") if p]
    return "".join(p[:1].upper() + p[1:] for p in parts)

icons = sorted(SRC_DIR.glob("*.4bpp"))
if not icons:
    raise SystemExit(f"No .4bpp icons found in {SRC_DIR}")

lines = []
lines.append("// Auto-generated. Do not edit by hand.")
lines.append('#pragma once')
lines.append('#include "global.h"')
lines.append('#include "graphics.h"')
lines.append("")
lines.append("// Spaceworld shared menu icon tiles (32x32, 4bpp = 512 bytes each)")
lines.append("")

for p in icons:
    base = p.stem  # e.g. 'humanshape'
    sym  = f"gSwIcon_{camel(base)}"
    rel  = p.as_posix()
    lines.append(f'const u8 {sym}[] = INCBIN_U8("{rel}");')

OUT_H.parent.mkdir(parents=True, exist_ok=True)
OUT_H.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"Wrote {OUT_H} with {len(icons)} icons.")
