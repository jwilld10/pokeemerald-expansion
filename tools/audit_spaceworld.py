#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Dict, List, Tuple

REPO = Path.cwd()

@dataclass
class SpeciesAudit:
    species_symbol: str                  # e.g. SPECIES_BULBASAUR_SW
    base_symbol: Optional[str] = None    # e.g. SPECIES_BULBASAUR (if detectable)
    species_id_defined_in: Optional[Path] = None
    species_info_file: Optional[Path] = None
    species_info_has_entry: bool = False
    gender_ratio: Optional[str] = None
    has_front_pic: bool = False
    has_back_pic: bool = False
    has_icon: bool = False
    has_normal_pal: bool = False
    has_shiny_pal: bool = False
    has_front_f_pic: bool = False
    has_back_f_pic: bool = False
    wired_front_f_in_speciesinfo: bool = False
    wired_back_f_in_speciesinfo: bool = False
    learnset_mentioned: bool = False
    evo_mentioned: bool = False
    dex_mentioned: bool = False
    warnings: List[str] = None
    errors: List[str] = None

    def __post_init__(self):
        self.warnings = []
        self.errors = []

def read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="ignore")

def find_files(globs: List[str], roots: List[Path]) -> List[Path]:
    out: List[Path] = []
    for root in roots:
        for g in globs:
            out.extend(root.glob(g))
    return [p for p in out if p.exists()]

def ripgrep_like(pattern: re.Pattern, roots: List[Path], exts=(".c",".h",".inc")) -> List[Path]:
    hits = []
    for root in roots:
        if not root.exists():
            continue
        for p in root.rglob("*"):
            if not p.is_file():
                continue
            if p.suffix not in exts:
                continue
            try:
                t = read_text(p)
            except Exception:
                continue
            if pattern.search(t):
                hits.append(p)
    return hits

def parse_species_sw_symbols() -> Dict[str, Path]:
    """
    Find all SPECIES_*_SW defines in include/constants (and anywhere else),
    returning symbol -> file defining it.
    """
    rx = re.compile(r"^\s*#define\s+(SPECIES_[A-Z0-9_]+_SW)\b", re.M)
    hits = {}
    for root in [REPO / "include", REPO / "src"]:
        if not root.exists():
            continue
        for p in root.rglob("*"):
            if not p.is_file():
                continue
            if p.suffix not in (".h", ".c", ".inc"):
                continue
            try:
                t = read_text(p)
            except Exception:
                continue
            for m in rx.finditer(t):
                sym = m.group(1)
                # Prefer include/constants if duplicates exist
                if sym not in hits or ("include/constants" in str(p).replace("\\","/")):
                    hits[sym] = p
    return hits

def locate_species_info_sources() -> List[Path]:
    """
    Find files likely containing gSpeciesInfo entries.
    pokeemerald-expansion often uses src/data/pokemon/species_info/*.h includes.
    """
    candidates: List[Path] = []
    # common locations
    for p in find_files(
        ["src/data/pokemon/species_info*.h", "src/data/pokemon/species_info/*.h", "src/data/pokemon/species_info/**/*.h"],
        [REPO]
    ):
        candidates.append(p)

    # also include any generated spaceworld files
    gen_dir = REPO / "src/data/pokemon/spaceworld_generated"
    if gen_dir.exists():
        candidates.extend(list(gen_dir.rglob("*.h")))

    # de-dup
    uniq = []
    seen = set()
    for p in candidates:
        if p in seen:
            continue
        seen.add(p)
        uniq.append(p)
    return uniq

def extract_species_block(text: str, species_sym: str) -> Optional[str]:
    # Matches: [SPECIES_X] = { ... },
    pat = re.compile(rf"\[\s*{re.escape(species_sym)}\s*\]\s*=\s*\{{(.*?)\n\}},", re.S)
    m = pat.search(text)
    if not m:
        return None
    return m.group(1)

def detect_gender_ratio(block: str) -> Optional[str]:
    # Attempt to capture .genderRatio assignment
    m = re.search(r"\.genderRatio\s*=\s*([^,\n]+)", block)
    if not m:
        return None
    return m.group(1).strip()

def locate_graphics_root() -> Optional[Path]:
    """
    Try to locate where Spaceworld graphics are stored.
    We'll heuristically look for directories that contain many *_sw or 'spaceworld' pokemon graphics.
    """
    # common places people put them
    guesses = [
        REPO / "graphics/pokemon",
        REPO / "graphics/pokemon/spaceworld",
        REPO / "graphics/spaceworld",
        REPO / "graphics/pokemon/spaceworld_pokemon",
        REPO / "graphics/pokemon/spaceworld_pokemon_gfx",
    ]
    for g in guesses:
        if g.exists():
            return g

    # heuristic: find a "spaceworld" directory under graphics
    gfx = REPO / "graphics"
    if gfx.exists():
        for p in gfx.rglob("*"):
            if p.is_dir() and "spaceworld" in p.name.lower():
                return p
    return None

def species_dir_candidates(graphics_root: Path, species_sym: str) -> List[Path]:
    """
    Try multiple conventions:
    - graphics_root/<monname>_sw
    - graphics_root/spaceworld/<monname>
    - graphics_root/spaceworld/<monname>_sw
    We derive monname from SPECIES_FOO_SW -> foo (lower)
    """
    mon = species_sym.replace("SPECIES_", "").replace("_SW","").lower()
    cands = []
    cands.append(graphics_root / f"{mon}_sw")
    cands.append(graphics_root / mon)
    cands.append(graphics_root / "spaceworld" / mon)
    cands.append(graphics_root / "spaceworld" / f"{mon}_sw")
    cands.append(graphics_root / "pokemon" / "spaceworld" / mon)
    cands.append(graphics_root / "pokemon" / "spaceworld" / f"{mon}_sw")
    return [c for c in cands if c.exists()]

def check_asset_files(dirpath: Path) -> Dict[str, bool]:
    """
    Accept many possible extensions because different repos store processed assets differently.
    """
    # front / back
    front = any((dirpath / f).exists() for f in ["front.png","front.4bpp.lz","front.4bpp","front.lz"])
    back  = any((dirpath / f).exists() for f in ["back.png","back.4bpp.lz","back.4bpp","back.lz"])
    # female variants
    front_f = any((dirpath / f).exists() for f in ["front_f.png","frontFemale.png","front_f.4bpp.lz","front_f.4bpp","front_f.lz"])
    back_f  = any((dirpath / f).exists() for f in ["back_f.png","backFemale.png","back_f.4bpp.lz","back_f.4bpp","back_f.lz"])
    # icon
    icon = any((dirpath / f).exists() for f in ["icon.png","icon.4bpp.lz","icon.4bpp","icon.lz"])
    # palettes
    normal_pal = any((dirpath / f).exists() for f in ["normal.pal","normal.gbapal","palette.pal","pal.pal","front.pal","normal.pal.lz"])
    shiny_pal  = any((dirpath / f).exists() for f in ["shiny.pal","shiny.gbapal","palette_shiny.pal","shiny.pal.lz"])
    return {
        "front": front, "back": back, "icon": icon,
        "front_f": front_f, "back_f": back_f,
        "normal_pal": normal_pal, "shiny_pal": shiny_pal,
    }

def find_generated_file_mentions() -> Dict[str, Optional[Path]]:
    """
    Locate your generated Spaceworld data files if present.
    """
    gen = REPO / "src/data/pokemon/spaceworld_generated"
    out = {"learnsets": None, "dex": None, "evos": None}
    if not gen.exists():
        return out
    # heuristics: find files with "learnset", "dex", "evo" in names
    for p in gen.rglob("*.h"):
        name = p.name.lower()
        if out["learnsets"] is None and "learnset" in name:
            out["learnsets"] = p
        if out["dex"] is None and ("dex" in name and "text" in name):
            out["dex"] = p
        if out["evos"] is None and ("evo" in name or "evolution" in name):
            out["evos"] = p
    return out

def main() -> int:
    species_defs = parse_species_sw_symbols()
    if not species_defs:
        print("ERROR: Could not find any '#define SPECIES_*_SW' in repo.")
        print("       If your Spaceworld species do not use _SW suffix, this auditor needs that convention.")
        return 2

    info_sources = locate_species_info_sources()
    gfx_root = locate_graphics_root()
    gen_files = find_generated_file_mentions()

    print(f"Repo: {REPO}")
    print(f"Found Spaceworld species defines: {len(species_defs)}")
    print(f"Species info candidate files:     {len(info_sources)}")
    print(f"Graphics root guess:              {gfx_root if gfx_root else 'NOT FOUND'}")
    print(f"Generated learnsets file:         {gen_files['learnsets'] if gen_files['learnsets'] else 'NOT FOUND'}")
    print(f"Generated dex text file:          {gen_files['dex'] if gen_files['dex'] else 'NOT FOUND'}")
    print(f"Generated evos file:              {gen_files['evos'] if gen_files['evos'] else 'NOT FOUND'}")
    print()

    # Preload generated text (optional)
    learn_txt = read_text(gen_files["learnsets"]) if gen_files["learnsets"] else ""
    dex_txt   = read_text(gen_files["dex"]) if gen_files["dex"] else ""
    evo_txt   = read_text(gen_files["evos"]) if gen_files["evos"] else ""

    audits: List[SpeciesAudit] = []
    for sym, def_file in sorted(species_defs.items()):
        a = SpeciesAudit(species_symbol=sym, species_id_defined_in=def_file)

        # Find species info entry
        entry_found = False
        for f in info_sources:
            try:
                t = read_text(f)
            except Exception:
                continue
            block = extract_species_block(t, sym)
            if block:
                a.species_info_file = f
                a.species_info_has_entry = True
                a.gender_ratio = detect_gender_ratio(block)
                # detect if female pics wired
                a.wired_front_f_in_speciesinfo = (".frontPicFemale" in block) or (".frontPicFemaleTable" in block)
                a.wired_back_f_in_speciesinfo  = (".backPicFemale" in block)  or (".backPicFemaleTable" in block)
                entry_found = True
                break
        if not entry_found:
            a.errors.append("Missing gSpeciesInfo entry for this species symbol in species_info sources.")

        # Generated mentions
        a.learnset_mentioned = (sym in learn_txt) if learn_txt else False
        a.dex_mentioned = (sym in dex_txt) if dex_txt else False
        a.evo_mentioned = (sym in evo_txt) if evo_txt else False

        if gen_files["learnsets"] and not a.learnset_mentioned:
            a.warnings.append("Not mentioned in generated learnsets file (may be OK if learnsets are elsewhere).")
        if gen_files["dex"] and not a.dex_mentioned:
            a.warnings.append("Not mentioned in generated dex text file (may be OK if dex text is elsewhere).")
        if gen_files["evos"] and not a.evo_mentioned:
            a.warnings.append("Not mentioned in generated evos file (may be OK if evos are elsewhere).")

        # Graphics checks
        if gfx_root:
            dirs = species_dir_candidates(gfx_root, sym)
            if not dirs:
                # broaden: search by folder name containing mon and sw
                mon = sym.replace("SPECIES_","").replace("_SW","").lower()
                candidates = []
                for p in gfx_root.rglob("*"):
                    if p.is_dir():
                        n = p.name.lower()
                        if mon in n and ("sw" in n or "spaceworld" in str(p).lower()):
                            candidates.append(p)
                dirs = candidates[:5]

            if not dirs:
                a.errors.append("Could not locate graphics directory for this species (searched common conventions).")
            else:
                # pick best directory (most files present)
                best = None
                best_score = -1
                best_assets = None
                for d in dirs:
                    assets = check_asset_files(d)
                    score = sum(1 for v in assets.values() if v)
                    if score > best_score:
                        best = d
                        best_score = score
                        best_assets = assets
                assets = best_assets or {}
                a.has_front_pic = assets.get("front", False)
                a.has_back_pic = assets.get("back", False)
                a.has_icon = assets.get("icon", False)
                a.has_normal_pal = assets.get("normal_pal", False)
                a.has_shiny_pal = assets.get("shiny_pal", False)
                a.has_front_f_pic = assets.get("front_f", False)
                a.has_back_f_pic = assets.get("back_f", False)

                if not a.has_front_pic: a.errors.append(f"Missing front sprite in graphics dir: {best}")
                if not a.has_back_pic:  a.errors.append(f"Missing back sprite in graphics dir: {best}")
                if not a.has_icon:      a.warnings.append(f"Missing icon in graphics dir: {best} (if you store icons elsewhere, ignore).")
                if not a.has_normal_pal:a.errors.append(f"Missing normal palette in graphics dir: {best}")
                if not a.has_shiny_pal: a.errors.append(f"Missing shiny palette in graphics dir: {best}")

                # Male/female sprite logic warnings
                # If female sprite exists but not wired, warn
                if a.has_front_f_pic and not a.wired_front_f_in_speciesinfo:
                    a.warnings.append("Has front_f sprite on disk but species_info does not appear to wire a female front pic pointer.")
                if a.has_back_f_pic and not a.wired_back_f_in_speciesinfo:
                    a.warnings.append("Has back_f sprite on disk but species_info does not appear to wire a female back pic pointer.")

                # If gender ratio is single-sex, warn about dead alternate sprite
                if a.gender_ratio:
                    gr = a.gender_ratio
                    single_female = ("MON_FEMALE" in gr) or ("PERCENT_FEMALE(100" in gr)
                    single_male   = ("MON_MALE" in gr)   or ("PERCENT_FEMALE(0" in gr)
                    if single_female and a.has_front_f_pic:
                        a.warnings.append("genderRatio appears all-female, but you also have a front_f sprite (female alt will never be 'male' unless you changed ratio intentionally).")
                    if single_male and a.has_front_f_pic:
                        a.warnings.append("genderRatio appears all-male, but you also have a front_f sprite (female alt will never be used unless ratio changed).")
        else:
            a.warnings.append("Graphics root not found; skipped sprite/palette checks.")

        audits.append(a)

    # Print report
    total = len(audits)
    err_count = sum(1 for a in audits if a.errors)
    warn_count = sum(len(a.warnings) for a in audits)
    print(f"=== Spaceworld Audit Summary ===")
    print(f"Species audited: {total}")
    print(f"Species with errors: {err_count}")
    print(f"Total warnings: {warn_count}")
    print()

    # Show details
    for a in audits:
        if not a.errors and not a.warnings:
            continue
        print(f"- {a.species_symbol}")
        if a.species_id_defined_in:
            print(f"  define: {a.species_id_defined_in}")
        if a.species_info_file:
            print(f"  species_info: {a.species_info_file}")
        if a.gender_ratio:
            print(f"  genderRatio: {a.gender_ratio}")
        if a.errors:
            for e in a.errors:
                print(f"  ERROR: {e}")
        if a.warnings:
            for w in a.warnings:
                print(f"  WARN:  {w}")
        print()

    # Exit nonzero if errors exist
    return 1 if err_count else 0

if __name__ == "__main__":
    raise SystemExit(main())
