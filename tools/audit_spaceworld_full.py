#!/usr/bin/env python3
from __future__ import annotations
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Dict

REPO = Path.cwd()

@dataclass
class Result:
    sym: str
    mon_folder: Optional[str] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

def read(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="ignore")

def load_syms() -> List[str]:
    f = REPO / "tools/spaceworld_species_symbols.txt"
    if not f.exists():
        raise SystemExit("ERROR: tools/spaceworld_species_symbols.txt not found.")
    syms = [ln.strip() for ln in f.read_text().splitlines() if ln.strip()]
    if not syms:
        raise SystemExit("ERROR: tools/spaceworld_species_symbols.txt is empty.")
    return syms

def species_info_block_exists(sym: str) -> bool:
    base = REPO / "src" / "data" / "pokemon"
    if not base.exists():
        return False
    rx = re.compile(rf"\[\s*{re.escape(sym)}\s*\]\s*=\s*\{{", re.M)
    for p in base.rglob("*"):
        if p.is_file() and p.suffix in (".h",".c",".inc"):
            if rx.search(read(p)):
                return True
    return False

def gfx_root() -> Path:
    p = REPO / "graphics" / "spaceworld" / "pokemon"
    if p.exists() and p.is_dir():
        return p
    raise SystemExit("ERROR: graphics/spaceworld/pokemon not found in repo.")

def icons_root() -> Path:
    # shared icon dir (your stated path)
    p = REPO / "graphics" / "spaceworld" / "icons"
    return p

def find_spaceworld_gfx_table() -> Path:
    # find the real file in repo, regardless of include path spelling
    matches = list(REPO.rglob("spaceworld_pokemon_gfx.h"))
    if not matches:
        raise SystemExit("ERROR: Could not find spaceworld_pokemon_gfx.h anywhere in repo.")
    # prefer the canonical data/graphics one if multiple exist
    for p in matches:
        s = str(p).replace("\\", "/")
        if "/data/graphics/" in s or "/src/data/graphics/" in s:
            return p
    return matches[0]

def derive_folder_from_gfx_table(gfx_text: str, sym: str) -> Optional[str]:
    """
    Look for the species symbol and extract the referenced gMonFrontPic_* slug.
    Example patterns in various forks:
      [SPECIES_X] = { .frontPic = gMonFrontPic_BLOSSOMITE, ... }
      {SPECIES_X, gMonFrontPic_BLOSSOMITE, ...}
      .frontPic = gMonFrontPic_MR__MIME
    """
    # Find a small window around where SPECIES appears, then search for gMonFrontPic_*
    idx = gfx_text.find(sym)
    if idx == -1:
        return None

    window = gfx_text[max(0, idx - 400) : min(len(gfx_text), idx + 800)]
    m = re.search(r"gMonFrontPic_([A-Z0-9_]+)", window)
    if not m:
        # sometimes it might be gMonFrontPicTable_ etc; broaden a bit
        m = re.search(r"FrontPic_([A-Z0-9_]+)", window)
        if not m:
            return None

    slug = m.group(1)
    # folder name convention in pokeemerald-style repos is lowercase slug
    # and double underscores should remain (mr__mime)
    return slug.lower()

def any_exists(dirp: Path, names: List[str]) -> bool:
    return any((dirp / n).exists() for n in names)

def check_mon_assets(gfx_root_dir: Path, folder: str, r: Result):
    gdir = gfx_root_dir / folder
    if not gdir.exists():
        r.errors.append(f"Missing graphics folder for mon at: {gdir}")
        return

    front_names = [
        "anim_front.png","anim_front.4bpp","anim_front.lz","anim_front.4bpp.lz",
        "anim_frontf.png","anim_frontf.4bpp","anim_frontf.lz","anim_frontf.4bpp.lz",
        "front.png","front.4bpp","front.lz","front.4bpp.lz",
        "front_f.png","front_f.4bpp","front_f.lz","front_f.4bpp.lz",
    ]
    back_names = [
        "anim_back.png","anim_back.4bpp","anim_back.lz","anim_back.4bpp.lz",
        "anim_backf.png","anim_backf.4bpp","anim_backf.lz","anim_backf.4bpp.lz",
        "back.png","back.4bpp","back.lz","back.4bpp.lz",
        "back_f.png","back_f.4bpp","back_f.lz","back_f.4bpp.lz",
    ]

    if not any_exists(gdir, front_names):
        r.errors.append("Missing front sprite asset (expected anim_front* or front*).")
    if not any_exists(gdir, back_names):
        r.errors.append("Missing back sprite asset (expected anim_back* or back*).")

    # Palettes
    normal_ok = any_exists(gdir, [
        "normal.gbapal","palette.gbapal","pal.gbapal",
        "anim_front.gbapal","anim_back.gbapal",
        "front.gbapal","back.gbapal",
    ])
    shiny_ok = any_exists(gdir, [
        "shiny.gbapal","anim_front_shiny.gbapal","anim_back_shiny.gbapal",
        "front_shiny.gbapal","back_shiny.gbapal","shiny_palette.gbapal",
        # some repos keep overworld shiny too; not required for battle sprites
        "overworld_shiny.gbapal",
    ])
    if not normal_ok:
        r.errors.append("Missing normal palette asset (normal/palette/pal/*front*.gbapal etc not found).")
    if not shiny_ok:
        r.errors.append("Missing shiny palette asset (shiny*.gbapal not found).")

def generated_dir_has_species_token(gen_dir: Path, sym: str, must_contain_any: List[re.Pattern]) -> bool:
    token = re.compile(rf"\b{re.escape(sym)}\b")
    for p in gen_dir.rglob("*"):
        if not (p.is_file() and p.suffix in (".h",".c",".inc")):
            continue
        t = read(p)
        if not token.search(t):
            continue
        if any(rx.search(t) for rx in must_contain_any):
            return True
    return False

def main() -> int:
    syms = load_syms()

    gen_dir = REPO / "src" / "data" / "pokemon" / "spaceworld_generated"
    if not gen_dir.exists():
        print("ERROR: src/data/pokemon/spaceworld_generated not found.")
        return 2

    gfx_dir = gfx_root()
    icon_dir = icons_root()

    gfx_table = find_spaceworld_gfx_table()
    gfx_text = read(gfx_table)

    print(f"Using Spaceworld gfx root:   {gfx_dir}")
    print(f"Using Spaceworld gfx table:  {gfx_table}")
    print(f"Using Spaceworld icons root: {icon_dir} (shared)")
    if not icon_dir.exists():
        print("WARN: Shared icons dir does not exist (expected).")
    print()

    learnset_markers = [
        re.compile(r"\bLEVEL_UP_MOVE\b"),
        re.compile(r"\bsLevelUpLearnset\b"),
        re.compile(r"\.levelUpLearnset\b"),
    ]
    dex_markers = [
        re.compile(r"\bPokedexEntry\b"),
        re.compile(r"\.description\b"),
        re.compile(r"\.categoryName\b"),
        re.compile(r"\.speciesName\b"),
    ]
    evo_markers = [
        re.compile(r"\bEVOLUTION\s*\("),
        re.compile(r"\.evolutions\b"),
    ]

    results: List[Result] = []

    missing_in_gfx_table = 0

    for sym in syms:
        r = Result(sym=sym)

        if not species_info_block_exists(sym):
            r.errors.append("Missing gSpeciesInfo block ([SPECIES_*] entry).")

        folder = derive_folder_from_gfx_table(gfx_text, sym)
        if folder is None:
            missing_in_gfx_table += 1
            r.errors.append("Could not derive graphics folder from spaceworld_pokemon_gfx.h (species not wired / not found).")
        else:
            r.mon_folder = folder
            check_mon_assets(gfx_dir, folder, r)

        if not generated_dir_has_species_token(gen_dir, sym, learnset_markers):
            r.errors.append("No learnset wiring found for species in spaceworld_generated (LEVEL_UP_MOVE / sLevelUpLearnset / .levelUpLearnset).")

        if not generated_dir_has_species_token(gen_dir, sym, dex_markers):
            r.errors.append("No dex text wiring found for species in spaceworld_generated (PokedexEntry / .description / .categoryName / .speciesName).")

        # evolutions are legitimately absent for fully-evolved / standalones
        if not generated_dir_has_species_token(gen_dir, sym, evo_markers):
            r.warnings.append("No evolutions wiring found in spaceworld_generated (may be fine for fully-evolved / standalones).")

        results.append(r)

    bad = [x for x in results if x.errors]
    warn_count = sum(len(x.warnings) for x in results)

    print("=== Summary (Spaceworld contract audit) ===")
    print(f"Species audited: {len(results)}")
    print(f"Species with ERRORS: {len(bad)}")
    print(f"Total WARNINGS: {warn_count}")
    print(f"Species missing from gfx table (cannot map folder): {missing_in_gfx_table}")
    print()

    for r in results:
        if not r.errors and not r.warnings:
            continue
        folder_str = f" (folder: {r.mon_folder})" if r.mon_folder else ""
        print(f"- {r.sym}{folder_str}")
        for e in r.errors:
            print(f"  ERROR: {e}")
        for w in r.warnings:
            print(f"  WARN:  {w}")
        print()

    return 1 if bad else 0

if __name__ == "__main__":
    raise SystemExit(main())
