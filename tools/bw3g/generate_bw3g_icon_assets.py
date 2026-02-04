#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
SPECIES_HDR = ROOT / "include/constants/species_bw3g.h"
ICON_DIR = ROOT / "graphics/bw3g/icons"

OUT_C = ROOT / "src/bw3g_mon_icons.c"
OUT_H = ROOT / "include/data/pokemon/bw3g_generated/bw3g_mon_icons.h"

SKIP_TOKENS = {"GENESIS_MON"}  # placeholder

def parse_species_tokens():
    rx = re.compile(r'^\s*#define\s+SPECIES_([A-Z0-9_]+)_BW3G\b')
    toks = []
    for ln in SPECIES_HDR.read_text(encoding="utf-8", errors="replace").splitlines():
        m = rx.match(ln)
        if m:
            toks.append(m.group(1))
    if not toks:
        raise SystemExit(f"[ERR] No SPECIES_*_BW3G parsed from {SPECIES_HDR}")
    return toks

def main():
    if not SPECIES_HDR.exists():
        raise SystemExit(f"[ERR] Missing: {SPECIES_HDR}")
    if not ICON_DIR.is_dir():
        raise SystemExit(f"[ERR] Missing BW3G icon dir: {ICON_DIR}")

    OUT_H.parent.mkdir(parents=True, exist_ok=True)

    tokens = parse_species_tokens()

    h = []
    h.append("// Auto-generated. Do not edit.\n")
    h.append("#ifndef GUARD_BW3G_MON_ICONS_H\n")
    h.append("#define GUARD_BW3G_MON_ICONS_H\n\n")
    h.append('#include "global.h"\n')
    h.append('#include "graphics.h"\n\n')

    c = []
    c.append("// Auto-generated. Do not edit.\n")
    c.append('#include "global.h"\n')
    c.append('#include "graphics.h"\n')
    c.append('#include "data/pokemon/bw3g_generated/bw3g_mon_icons.h"\n\n')

    missing = []
    written = 0

    for token in tokens:
        if token in SKIP_TOKENS:
            continue

        # Icons are lowercase filenames in your tree: snivy.4bpp, etc.
        fname = f"{token.lower()}.4bpp"
        f = ICON_DIR / fname
        if not f.exists():
            missing.append(token)
            continue

        sym = f"gBw3gMonIcon_{token.title().replace('_','')}"
        # NOTE: token format might be like "MR_MIME" → title() gives "Mr_Mime"
        # In your bw3g_families.h it looked like gBw3gMonIcon_Snivy style,
        # which matches title().replace('_','') approach for most.
        #
        # If your tokens are already in PascalCase somewhere else, we can switch to that,
        # but this should match your observed names like gBw3gMonIcon_Snivy.

        def rel(p: Path) -> str:
            return str(p.relative_to(ROOT)).replace("\\", "/")

        h.append(f"extern const u8 {sym}[];\n")
        c.append(f'ALIGNED(4) const u8 {sym}[] = INCBIN_U8("{rel(f)}");\n')

        written += 1

    h.append("\n#endif // GUARD_BW3G_MON_ICONS_H\n")

    OUT_H.write_text("".join(h), encoding="utf-8")
    OUT_C.write_text("".join(c), encoding="utf-8")

    print(f"[OK] Wrote: {OUT_H}")
    print(f"[OK] Wrote: {OUT_C}")
    print(f"[INFO] Species tokens: {len(tokens)}  Written: {written}  Missing: {len(missing)}")
    if missing:
        print("[INFO] First 30 missing icon files:")
        for t in missing[:30]:
            print("  -", t.lower() + ".4bpp")

if __name__ == "__main__":
    main()
