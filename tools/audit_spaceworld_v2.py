#!/usr/bin/env python3
from __future__ import annotations
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List

REPO = Path.cwd()

@dataclass
class Result:
    sym: str
    defined_in: Optional[Path] = None
    species_info_file: Optional[Path] = None
    has_species_info: bool = False
    gender_ratio: Optional[str] = None
    wired_front_f: bool = False
    wired_back_f: bool = False
    # assets
    gfx_dir: Optional[Path] = None
    has_front: bool = False
    has_back: bool = False
    has_icon: bool = False
    has_normal_pal: bool = False
    has_shiny_pal: bool = False
    has_front_f: bool = False
    has_back_f: bool = False
    errors: List[str] = field(default_factory=list)
    warns: List[str] = field(default_factory=list)

def read(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="ignore")

def find_define_file(sym: str) -> Optional[Path]:
    rx = re.compile(rf"^\s*#define\s+{re.escape(sym)}\b", re.M)
    for root in [REPO/"include", REPO/"src"]:
        if not root.exists(): continue
        for p in root.rglob("*"):
            if not p.is_file(): continue
            if p.suffix not in (".h",".c",".inc"): continue
            if rx.search(read(p)):
                return p
    return None

def species_info_files() -> List[Path]:
    out = []
    base = REPO / "src/data/pokemon"
    if base.exists():
        out += list(base.rglob("species_info*.h"))
        out += list((base/"species_info").rglob("*.h")) if (base/"species_info").exists() else []
    gen = REPO / "src/data/pokemon/spaceworld_generated"
    if gen.exists():
        out += list(gen.rglob("*.h"))
    # uniq
    seen=set(); uniq=[]
    for p in out:
        if p in seen: continue
        seen.add(p); uniq.append(p)
    return uniq

def extract_block(t: str, sym: str) -> Optional[str]:
    pat = re.compile(rf"\[\s*{re.escape(sym)}\s*\]\s*=\s*\{{(.*?)\n\}},", re.S)
    m = pat.search(t)
    return m.group(1) if m else None

def detect_gender_ratio(block: str) -> Optional[str]:
    m = re.search(r"\.genderRatio\s*=\s*([^,\n]+)", block)
    return m.group(1).strip() if m else None

def locate_gfx_root() -> Optional[Path]:
    # common guesses
    for g in [
        REPO/"graphics/pokemon",
        REPO/"graphics",
        REPO/"data/graphics",
    ]:
        if g.exists():
            return g
    return None

def best_species_gfx_dir(gfx_root: Path, sym: str) -> Optional[Path]:
    mon = sym.replace("SPECIES_","").lower()
    # Try common “spaceworld” containers first
    preferred_dirs = []
    for p in gfx_root.rglob("*"):
        if p.is_dir() and "spaceworld" in str(p).lower():
            preferred_dirs.append(p)

    search_roots = preferred_dirs if preferred_dirs else [gfx_root]

    best=None; best_score=-1
    for root in search_roots:
        for p in root.rglob("*"):
            if not p.is_dir(): continue
            n = p.name.lower()
            if mon in n:
                # score by presence of expected filenames
                score = 0
                for f in ["front.png","front.4bpp.lz","back.png","back.4bpp.lz","icon.png","icon.4bpp.lz",
                          "normal.gbapal","normal.pal","shiny.gbapal","shiny.pal","front_f.png","back_f.png"]:
                    if (p/f).exists(): score += 1
                if score > best_score:
                    best = p; best_score = score
    return best

def has_any(p: Path, names: List[str]) -> bool:
    return any((p/n).exists() for n in names)

def main() -> int:
    sym_file = REPO / "tools/spaceworld_species_symbols.txt"
    if not sym_file.exists():
        print("ERROR: tools/spaceworld_species_symbols.txt not found. Run the discovery script first.")
        return 2

    syms = [ln.strip() for ln in sym_file.read_text().splitlines() if ln.strip()]
    if not syms:
        print("ERROR: spaceworld_species_symbols.txt is empty.")
        return 2

    info_files = species_info_files()
    gfx_root = locate_gfx_root()

    print(f"Auditing {len(syms)} Spaceworld species symbols.")
    print(f"Species info candidates: {len(info_files)}")
    print(f"Graphics root guess: {gfx_root if gfx_root else 'NOT FOUND'}")
    print()

    results: List[Result] = []
    for sym in syms:
        r = Result(sym=sym)
        r.defined_in = find_define_file(sym)
        if not r.defined_in:
            r.warns.append("Could not find #define for species symbol (might be enum-based or generated elsewhere).")

        # species_info entry
        found = False
        for f in info_files:
            t = read(f)
            blk = extract_block(t, sym)
            if blk:
                r.species_info_file = f
                r.has_species_info = True
                r.gender_ratio = detect_gender_ratio(blk)
                r.wired_front_f = (".frontPicFemale" in blk) or (".frontPicFemaleTable" in blk)
                r.wired_back_f  = (".backPicFemale" in blk)  or (".backPicFemaleTable" in blk)
                found = True
                break
        if not found:
            r.errors.append("Missing gSpeciesInfo block for this symbol in species_info sources.")

        # graphics
        if gfx_root:
            d = best_species_gfx_dir(gfx_root, sym)
            r.gfx_dir = d
            if not d:
                r.errors.append("Could not locate graphics dir for species (heuristic search).")
            else:
                r.has_front = has_any(d, ["front.png","front.4bpp.lz","front.4bpp","front.lz"])
                r.has_back  = has_any(d, ["back.png","back.4bpp.lz","back.4bpp","back.lz"])
                r.has_icon  = has_any(d, ["icon.png","icon.4bpp.lz","icon.4bpp","icon.lz"])
                r.has_normal_pal = has_any(d, ["normal.gbapal","normal.pal","palette.pal","pal.pal","front.pal"])
                r.has_shiny_pal  = has_any(d, ["shiny.gbapal","shiny.pal","palette_shiny.pal"])

                r.has_front_f = has_any(d, ["front_f.png","frontFemale.png","front_f.4bpp.lz","front_f.4bpp"])
                r.has_back_f  = has_any(d, ["back_f.png","backFemale.png","back_f.4bpp.lz","back_f.4bpp"])

                if not r.has_front: r.errors.append("Missing front sprite file in graphics dir.")
                if not r.has_back:  r.errors.append("Missing back sprite file in graphics dir.")
                if not r.has_normal_pal: r.errors.append("Missing normal palette file in graphics dir.")
                if not r.has_shiny_pal:  r.errors.append("Missing shiny palette file in graphics dir.")

                # Female sprite wiring checks (warnings only)
                if r.has_front_f and not r.wired_front_f:
                    r.warns.append("Has front_f on disk but species_info doesn't appear to wire female front pic.")
                if r.has_back_f and not r.wired_back_f:
                    r.warns.append("Has back_f on disk but species_info doesn't appear to wire female back pic.")
        else:
            r.warns.append("Graphics root not found; skipped graphics checks.")

        results.append(r)

    err_species = [r for r in results if r.errors]
    warn_total = sum(len(r.warns) for r in results)

    print("=== Summary ===")
    print(f"Species audited: {len(results)}")
    print(f"Species with errors: {len(err_species)}")
    print(f"Total warnings: {warn_total}")
    print()

    for r in results:
        if not r.errors and not r.warns:
            continue
        print(f"- {r.sym}")
        if r.species_info_file: print(f"  species_info: {r.species_info_file}")
        if r.gfx_dir: print(f"  gfx_dir:      {r.gfx_dir}")
        if r.gender_ratio: print(f"  genderRatio:  {r.gender_ratio}")
        for e in r.errors:
            print(f"  ERROR: {e}")
        for w in r.warns:
            print(f"  WARN:  {w}")
        print()

    return 1 if err_species else 0

if __name__ == "__main__":
    raise SystemExit(main())
