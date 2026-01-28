#!/usr/bin/env python3
from __future__ import annotations
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

REPO = Path.cwd()

@dataclass
class Row:
    sym: str
    mon: str
    has_any_shiny_asset: bool = False
    shiny_asset_examples: List[str] = field(default_factory=list)
    species_info_block_found: bool = False
    species_info_mentions_shiny: bool = False
    species_info_mentions_palette_table: bool = False
    gfx_registry_has_shiny_table: bool = False
    errors: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

def read(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="ignore")

def load_species_symbols() -> List[str]:
    f = REPO / "tools/spaceworld_species_symbols.txt"
    if not f.exists():
        raise SystemExit("Missing tools/spaceworld_species_symbols.txt (run discovery script first).")
    syms = [ln.strip() for ln in f.read_text().splitlines() if ln.strip()]
    if not syms:
        raise SystemExit("tools/spaceworld_species_symbols.txt is empty.")
    return syms

def to_mon_name(sym: str) -> str:
    # SPECIES_ABRA_SPACEWORLD -> abra
    s = sym.replace("SPECIES_", "")
    s = s.replace("_SPACEWORLD", "")
    return s.lower()

def species_info_sources() -> List[Path]:
    out = []
    base = REPO / "src/data/pokemon"
    if (base / "spaceworld_generated").exists():
        out += list((base / "spaceworld_generated").rglob("*.h"))
    # also include any other species_info files that might contain these blocks
    out += list(base.rglob("species_info*.h")) if base.exists() else []
    # uniq
    seen=set(); uniq=[]
    for p in out:
        if p in seen: continue
        seen.add(p); uniq.append(p)
    return uniq

def extract_species_block(text: str, sym: str) -> Optional[str]:
    pat = re.compile(rf"\[\s*{re.escape(sym)}\s*\]\s*=\s*\{{(.*?)\n\}},", re.S)
    m = pat.search(text)
    return m.group(1) if m else None

def find_spaceworld_gfx_files() -> List[Path]:
    files = []
    for base in [REPO/"src", REPO/"include", REPO/"data", REPO/"src/data"]:
        if not base.exists(): 
            continue
        for p in base.rglob("*"):
            if not p.is_file(): 
                continue
            if p.suffix not in (".h",".inc",".c"):
                continue
            if "spaceworld" in str(p).lower():
                files.append(p)
    # uniq
    seen=set(); uniq=[]
    for p in files:
        if p in seen: continue
        seen.add(p); uniq.append(p)
    return uniq

def detect_shiny_table_presence(gfx_files: List[Path]) -> bool:
    """
    Checks if ANY spaceworld gfx file appears to define/mention a shiny palette table concept.
    We look for common patterns, not just the exact word 'shiny' near a species.
    """
    patterns = [
        r"ShinyPalette",
        r"SHINY",
        r"shiny",
        r"gMonShinyPalette",
        r"gShinyPalette",
        r"shinyPal",
        r"PAL_SHINY",
    ]
    rx = re.compile("|".join(patterns))
    for p in gfx_files:
        if rx.search(read(p)):
            return True
    return False

def find_shiny_assets_for_mon(mon: str) -> List[str]:
    """
    Searches the whole repo for files that look like they are this mon's shiny palette.
    This is asset-level truth (files exist), independent of wiring.
    """
    hits = []
    # Look for typical palette extensions used by pokeemerald-expansion pipelines
    exts = {".gbapal", ".pal", ".png"}
    # Only consider plausible graphics paths to keep it fast-ish
    roots = []
    for r in [REPO/"graphics", REPO/"data/graphics", REPO/"src/data/graphics", REPO/"src/data/pokemon", REPO/"src"]:
        if r.exists():
            roots.append(r)

    # Heuristic: filename contains mon and 'shiny' OR 'shiny' directory contains mon
    for root in roots:
        for p in root.rglob("*"):
            if not p.is_file():
                continue
            if p.suffix not in exts:
                continue
            name = p.name.lower()
            path = str(p).lower()
            if "shiny" in name or "/shiny" in path or "shiny_" in name:
                if mon in name or f"/{mon}" in path or f"_{mon}_" in name or name.startswith(mon):
                    hits.append(str(p))
    return hits[:10]  # keep output readable

def main() -> int:
    syms = load_species_symbols()
    info_files = species_info_sources()
    gfx_files = find_spaceworld_gfx_files()
    has_global_shiny_concept = detect_shiny_table_presence(gfx_files)

    print(f"Loaded {len(syms)} Spaceworld species symbols.")
    print(f"SpeciesInfo sources: {len(info_files)}")
    print(f"Spaceworld gfx-related files: {len(gfx_files)}")
    print(f"Detected ANY shiny palette concept in spaceworld gfx files: {has_global_shiny_concept}")
    print()

    # Preload species info texts
    info_texts: List[Tuple[Path,str]] = [(p, read(p)) for p in info_files]

    rows: List[Row] = []
    for sym in syms:
        mon = to_mon_name(sym)
        r = Row(sym=sym, mon=mon)

        # A) Asset existence
        shiny_assets = find_shiny_assets_for_mon(mon)
        if shiny_assets:
            r.has_any_shiny_asset = True
            r.shiny_asset_examples = shiny_assets
        else:
            r.errors.append("No shiny palette asset files found by heuristic search (may be stored in a table/header instead of files).")

        # B) SpeciesInfo wiring characteristics
        blk = None
        for p, t in info_texts:
            b = extract_species_block(t, sym)
            if b:
                blk = b
                r.species_info_block_found = True
                # detect direct shiny mention or table indirection
                if re.search(r"\bshiny\b", blk, re.I) or "Shiny" in blk:
                    r.species_info_mentions_shiny = True
                if re.search(r"paletteTable|palettes\s*=", blk):
                    r.species_info_mentions_palette_table = True
                break

        if not r.species_info_block_found:
            r.errors.append("Missing gSpeciesInfo block for this species symbol.")

        # C) Registry-level truth: if the repo has a shiny palette table concept anywhere,
        # then a lack of per-species 'shiny' text isn't an error.
        r.gfx_registry_has_shiny_table = has_global_shiny_concept
        if has_global_shiny_concept and not r.species_info_mentions_shiny:
            r.notes.append("Repo appears to use a shiny palette table/macro system; per-species blocks may not mention shiny directly.")

        rows.append(r)

    # Now decide what's truly a failure:
    # If you DO have a global shiny-table concept, then we only fail if species_info is missing.
    # If you DON'T, then we'd expect species_info to mention shiny or assets to exist clearly.
    failures: List[Row] = []
    for r in rows:
        if not r.species_info_block_found:
            failures.append(r)
        else:
            # If there's no global shiny concept detected, require either direct mention or assets.
            if not has_global_shiny_concept and (not r.species_info_mentions_shiny and not r.has_any_shiny_asset):
                failures.append(r)

    print("=== Summary (Shiny audit that respects table-based wiring) ===")
    print(f"Species audited: {len(rows)}")
    print(f"True failures: {len(failures)}")
    print()

    if failures:
        for r in failures[:30]:
            print(f"- {r.sym}")
            for e in r.errors:
                print(f"  ERROR: {e}")
            if r.shiny_asset_examples:
                print("  shiny asset examples:")
                for s in r.shiny_asset_examples[:3]:
                    print(f"    {s}")
            print()
        if len(failures) > 30:
            print(f"... plus {len(failures)-30} more")
        return 1

    # If no failures, show a sanity sample of shiny assets for first 5 mons
    print("No true failures detected.")
    print("\nSanity sample (first 5 mons with shiny assets found):")
    shown = 0
    for r in rows:
        if r.shiny_asset_examples:
            print(f"- {r.sym}:")
            for s in r.shiny_asset_examples[:2]:
                print(f"   {s}")
            shown += 1
            if shown >= 5:
                break

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
