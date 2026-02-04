#!/usr/bin/env python3
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
SPECIES_HDR = ROOT / "include/constants/species_bw3g.h"
GFX_ROOT = ROOT / "graphics/bw3g/pokemon"

OUT_C = ROOT / "src/bw3g_pokemon_pics.c"
OUT_H = ROOT / "include/data/pokemon/bw3g_generated/bw3g_pokemon_pics.h"

SKIP_TOKENS = {"GENESIS_MON"}  # placeholder troublemaker

def parse_species_tokens():
    if not SPECIES_HDR.exists():
        raise SystemExit(f"[ERR] Missing: {SPECIES_HDR}")

    toks = []
    rx = re.compile(r'^\s*#define\s+SPECIES_([A-Z0-9_]+)_BW3G\b')
    for ln in SPECIES_HDR.read_text(encoding="utf-8", errors="replace").splitlines():
        m = rx.match(ln)
        if m:
            toks.append(m.group(1))
    if not toks:
        raise SystemExit(f"[ERR] No SPECIES_*_BW3G parsed from {SPECIES_HDR}")
    return toks

def find_dir_for_token(token: str) -> Path | None:
    # Most folders are lowercase token (snivy, lairon, etc.)
    want = token.lower()
    d = GFX_ROOT / want
    if d.is_dir():
        return d
    # fallback: any folder matching case-insensitively
    for cand in GFX_ROOT.iterdir():
        if cand.is_dir() and cand.name.lower() == want:
            return cand
    return None

def pick_first(d: Path, patterns: list[str]) -> Path | None:
    for pat in patterns:
        hits = sorted(d.glob(pat))
        if hits:
            return hits[0]
    return None

def main():
    if not GFX_ROOT.is_dir():
        raise SystemExit(f"[ERR] Missing BW3G gfx dir: {GFX_ROOT}")

    tokens = parse_species_tokens()

    OUT_H.parent.mkdir(parents=True, exist_ok=True)

    h = []
    h.append("// Auto-generated. Do not edit.\n")
    h.append("#ifndef GUARD_BW3G_POKEMON_PICS_H\n")
    h.append("#define GUARD_BW3G_POKEMON_PICS_H\n\n")
    h.append('#include "global.h"\n')
    h.append('#include "graphics.h"\n\n')

    c = []
    c.append("// Auto-generated. Do not edit.\n")
    c.append('#include "global.h"\n')
    c.append('#include "graphics.h"\n')
    c.append('#include "data/pokemon/bw3g_generated/bw3g_pokemon_pics.h"\n\n')

    missing = []
    written = 0

    for token in tokens:
        if token in SKIP_TOKENS:
            continue

        d = find_dir_for_token(token)
        if d is None:
            missing.append((token, "dir"))
            continue

        # Be tolerant: BW3G may have various filenames.
        front = pick_first(d, ["front*.4bpp.lz", "front*.2bpp.lz", "front*.4bpp", "front*.2bpp"])
        back  = pick_first(d, ["back*.4bpp.lz",  "back*.2bpp.lz",  "back*.4bpp",  "back*.2bpp"])
        pal   = pick_first(d, ["normal*.gbapal", "normal*.pal", "normal*.gbapal.lz", "normal*.pal.lz"])
        shpal = pick_first(d, ["shiny*.gbapal",  "shiny*.pal",  "shiny*.gbapal.lz",  "shiny*.pal.lz"])

        # You can add anim/front/back assets later; this is the minimum to stop mapping to vanilla.
        if front is None or back is None or pal is None:
            missing.append((token, f"front={bool(front)} back={bool(back)} pal={bool(pal)}"))
            continue

        # Paths must be repo-relative for INCBIN.
        def rel(p: Path) -> str:
            return str(p.relative_to(ROOT)).replace("\\", "/")

        sym_front = f"gMonFrontPic_{token}Bw3g"
        sym_back  = f"gMonBackPic_{token}Bw3g"
        sym_pal   = f"gMonPalette_{token}Bw3g"
        sym_shpal = f"gMonShinyPalette_{token}Bw3g"

        # Externs
        h.append(f"extern const u8 {sym_front}[];\n")
        h.append(f"extern const u8 {sym_back}[];\n")
        h.append(f"extern const u8 {sym_pal}[];\n")
        if shpal is not None:
            h.append(f"extern const u8 {sym_shpal}[];\n")

        # Definitions (aligned for safety)
        c.append(f"ALIGNED(4) const u8 {sym_front}[] = INCBIN_U8(\"{rel(front)}\");\n")
        c.append(f"ALIGNED(4) const u8 {sym_back}[]  = INCBIN_U8(\"{rel(back)}\");\n")
        c.append(f"ALIGNED(4) const u8 {sym_pal}[]   = INCBIN_U8(\"{rel(pal)}\");\n")
        if shpal is not None:
            c.append(f"ALIGNED(4) const u8 {sym_shpal}[] = INCBIN_U8(\"{rel(shpal)}\");\n")
        c.append("\n")

        written += 1

    h.append("\n#endif // GUARD_BW3G_POKEMON_PICS_H\n")

    OUT_H.write_text("".join(h), encoding="utf-8")
    OUT_C.write_text("".join(c), encoding="utf-8")

    print(f"[OK] Wrote: {OUT_H}")
    print(f"[OK] Wrote: {OUT_C}")
    print(f"[INFO] Species tokens: {len(tokens)}  Written: {written}  Missing: {len(missing)}")
    if missing:
        print("[INFO] First 20 missing:")
        for t, why in missing[:20]:
            print(f"  - {t}: {why}")

if __name__ == "__main__":
    main()
