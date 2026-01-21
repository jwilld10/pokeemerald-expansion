#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import re
import subprocess

SPEC = Path("src/data/pokemon/spaceworld_generated/spaceworld_species_info.h")
GFXROOT = Path("graphics/spaceworld/pokemon")

ENTRY_HDR = re.compile(r'^\s*\[(SPECIES_[A-Z0-9_]+_SPACEWORLD)\]\s*=\s*$', re.M)

def identify_wh(p: Path):
    out = subprocess.check_output(["identify", "-format", "%w %h", str(p)], text=True).strip()
    w, h = out.split()
    return int(w), int(h)

def pick_front_png(mon_dir: Path) -> Path | None:
    p = mon_dir / "anim_front.png"
    return p if p.is_file() else None

def folder_from_species(tok: str) -> str:
    return tok.removeprefix("SPECIES_").removesuffix("_SPACEWORLD").lower()

def yoff_for(h: int) -> int:
    # How pokeemerald generally centers non-64 fronts inside 64 canvas.
    # This offsets the sprite downward a bit when smaller.
    return max(0, (64 - h) // 2)

def patch_block(block: str, w: int, h: int, yoff: int) -> str:
    # frontPicSize
    if re.search(r'\.frontPicSize\s*=', block):
        block = re.sub(r'\.frontPicSize\s*=\s*MON_COORDS_SIZE\([^)]*\)\s*,',
                       f'.frontPicSize = MON_COORDS_SIZE({w}, {h}),', block)
    else:
        block = re.sub(r'(\.frontPic\s*=\s*[^,]+,\s*\n)',
                       r'\1    .frontPicSize = MON_COORDS_SIZE(%d, %d),\n' % (w, h),
                       block, count=1)

    # frontPicYOffset
    if re.search(r'\.frontPicYOffset\s*=', block):
        block = re.sub(r'\.frontPicYOffset\s*=\s*\d+\s*,',
                       f'.frontPicYOffset = {yoff},', block)
    else:
        block = re.sub(r'(\.frontPicSize\s*=\s*MON_COORDS_SIZE\([^)]*\)\s*,\s*\n)',
                       r'\1    .frontPicYOffset = %d,\n' % yoff,
                       block, count=1)
    return block

def main():
    text = SPEC.read_text(encoding="utf-8")
    patched = 0

    for m in list(ENTRY_HDR.finditer(text)):
        tok = m.group(1)
        folder = folder_from_species(tok)
        mon_dir = GFXROOT / folder
        front = pick_front_png(mon_dir)
        if not front:
            continue

        w, h = identify_wh(front)
        yoff = yoff_for(h)

        # find block start and end
        brace = text.find("{", m.start())
        end = text.find("},", brace)
        if brace == -1 or end == -1:
            continue
        block = text[brace:end+2]

        new_block = patch_block(block, w, h, yoff)
        if new_block != block:
            text = text[:brace] + new_block + text[end+2:]
            patched += 1

    SPEC.write_text(text, encoding="utf-8")
    print(f"Patched entries: {patched}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
