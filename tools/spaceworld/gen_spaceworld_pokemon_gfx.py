#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import re
import sys

REPO = Path.cwd()
GFX_ROOT = REPO / "graphics" / "spaceworld" / "pokemon"

UNOWN_FORM_RE = re.compile(r"^unown_([a-z])$", re.I)

def c_ident_from_folder(folder: str) -> str:
    # General folder -> C identifier rules
    # Examples: mr__mime -> MrMime, ho_oh -> HoOh, mimejr -> MimeJr, tangtrip -> Tangtrip
    f = folder.strip().lower()

    # Special-case Unown letter forms: unown_f => UnownFormF
    m = UNOWN_FORM_RE.match(f)
    if m:
        return "UnownForm" + m.group(1).upper()

    parts = re.split(r"[_\-\s]+", f)
    out: list[str] = []
    for p in parts:
        if not p:
            continue
        if p == "jr":
            out.append("Jr")
            continue
        if p == "mr":
            out.append("Mr")
            continue
        if p == "mime":
            out.append("Mime")
            continue
        if p == "ho":
            out.append("Ho")
            continue
        if p == "oh":
            out.append("Oh")
            continue
        out.append(p[0].upper() + p[1:])
    return "".join(out)

def has_female_variant(mon_dir: Path) -> bool:
    # Only generate female symbols if frontf PNG exists
    return (mon_dir / "anim_frontf.png").is_file()

def main() -> int:
    if not GFX_ROOT.is_dir():
        print(f"Missing: {GFX_ROOT}. Did you run import_spaceworld_sprites.py?", file=sys.stderr)
        return 1

    mons = [p for p in sorted(GFX_ROOT.iterdir()) if p.is_dir()]
    if not mons:
        print("No mons found under graphics/spaceworld/pokemon", file=sys.stderr)
        return 1

    out_h = REPO / "src" / "data" / "graphics" / "spaceworld_pokemon_gfx.h"
    out_c = REPO / "src" / "data" / "graphics" / "spaceworld_pokemon_gfx.c"

    h_lines: list[str] = []
    c_lines: list[str] = []

    h_lines += [
        "#ifndef GUARD_SPACEWORLD_POKEMON_GFX_H",
        "#define GUARD_SPACEWORLD_POKEMON_GFX_H",
        "",
        "#include \"global.h\"",
        "",
    ]
    c_lines += [
        "#include \"global.h\"",
        "#include \"data/graphics/spaceworld_pokemon_gfx.h\"",
        "",
    ]

    def emit_one(mon_dir: Path) -> None:
        folder = mon_dir.name
        ident = c_ident_from_folder(folder)

        # Base Unown must never be gendered.
        is_unown_base = folder.lower() == "unown"
        is_unown_form = UNOWN_FORM_RE.match(folder) is not None

        emit_female = (not is_unown_base) and (not is_unown_form) and has_female_variant(mon_dir)

        # Files (we reference .4bpp.smol / .gbapal as produced by your build rules)
        front_smol = f"graphics/spaceworld/pokemon/{folder}/anim_front.4bpp.smol"
        back_smol  = f"graphics/spaceworld/pokemon/{folder}/back.4bpp.smol"

        # Unown exception in Spaceworld source naming:
        # most: normal palette is front.gbcpal -> normal.gbapal in your repo
        # unown: normal.pal exists upstream; in your repo you said you normalize it, so we still use normal.gbapal
        normal_pal = f"graphics/spaceworld/pokemon/{folder}/normal.gbapal"
        shiny_pal  = f"graphics/spaceworld/pokemon/{folder}/shiny.gbapal"

        h_lines.append(f"extern const u32 gSwMonFrontPic_{ident}[];")
        h_lines.append(f"extern const u32 gSwMonBackPic_{ident}[];")
        h_lines.append(f"extern const u16 gSwMonPalette_{ident}[];")
        h_lines.append(f"extern const u16 gSwMonShinyPalette_{ident}[];")
        h_lines.append("")

        c_lines.append(f'const u32 gSwMonFrontPic_{ident}[] = INCBIN_U32("{front_smol}");')
        c_lines.append(f'const u32 gSwMonBackPic_{ident}[]  = INCBIN_U32("{back_smol}");')
        c_lines.append(f'const u16 gSwMonPalette_{ident}[]  = INCBIN_U16("{normal_pal}");')
        c_lines.append(f'const u16 gSwMonShinyPalette_{ident}[] = INCBIN_U16("{shiny_pal}");')

        if emit_female:
            frontf_smol = f"graphics/spaceworld/pokemon/{folder}/anim_frontf.4bpp.smol"
            h_lines.append(f"extern const u32 gSwMonFrontPic_{ident}F[];")
            h_lines.append("")
            c_lines.append(f'const u32 gSwMonFrontPic_{ident}F[] = INCBIN_U32("{frontf_smol}");')

        c_lines.append("")

    for mon in mons:
        emit_one(mon)

    # Keep your Unown letter-form compatibility mapping (species/constants often refer to UnownF, etc.)
    # The generator now emits UnownFormF symbols, so mapping can live in the header.
    h_lines += [
        "/* --- Unown letter-form collision fix ---",
        " * UnownFormX symbols are used for Unown letter forms (unown_a..unown_z).",
        " * If other code expects legacy gSwMon*UnownF for the F form, map it here.",
        " */",
        "#define gSwMonFrontPic_UnownF         gSwMonFrontPic_UnownFormF",
        "#define gSwMonBackPic_UnownF          gSwMonBackPic_UnownFormF",
        "#define gSwMonPalette_UnownF          gSwMonPalette_UnownFormF",
        "#define gSwMonShinyPalette_UnownF     gSwMonShinyPalette_UnownFormF",
        "",
        "#endif // GUARD_SPACEWORLD_POKEMON_GFX_H",
        "",
    ]

    out_h.write_text("\n".join(h_lines), encoding="utf-8")
    out_c.write_text("\n".join(c_lines), encoding="utf-8")
    print(f"Wrote {out_h}")
    print(f"Wrote {out_c}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
