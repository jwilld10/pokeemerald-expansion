#!/usr/bin/env python3
from __future__ import annotations
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional

REPO = Path.cwd()

@dataclass
class Row:
    sym: str
    species_info_ok: bool = False
    gfx_mentions: bool = False
    icon_mentions: bool = False
    shiny_mentions: bool = False
    errors: List[str] = field(default_factory=list)

def read(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="ignore")

def gather_spaceworld_files() -> dict[str, List[Path]]:
    """
    Finds likely Spaceworld graphics registry headers/incs.
    We don't assume folder layout; we search for filenames/paths containing 'spaceworld'
    and also known headers referenced by your includes.
    """
    buckets = {"gfx": [], "icons": [], "other": []}

    # Known/common locations
    candidates = []
    for base in [REPO/"src", REPO/"include", REPO/"data", REPO/"src/data"]:
        if base.exists():
            candidates += list(base.rglob("*.h"))
            candidates += list(base.rglob("*.inc"))
            candidates += list(base.rglob("*.c"))

    for p in candidates:
        lp = str(p).lower()
        name = p.name.lower()
        if "spaceworld" not in lp and "spaceworld" not in name:
            continue
        # Bucket by intent
        if "icon" in name or "icons" in lp:
            buckets["icons"].append(p)
        elif "gfx" in name or "graphics" in lp or "pokemon_gfx" in name:
            buckets["gfx"].append(p)
        else:
            buckets["other"].append(p)

    # De-dup
    for k in buckets:
        seen = set()
        uniq = []
        for p in buckets[k]:
            if p in seen: continue
            seen.add(p)
            uniq.append(p)
        buckets[k] = uniq

    return buckets

def find_species_info_sources() -> List[Path]:
    out = []
    base = REPO / "src/data/pokemon"
    if base.exists():
        out += list((base/"spaceworld_generated").rglob("*.h")) if (base/"spaceworld_generated").exists() else []
        out += list(base.rglob("species_info*.h"))
    # uniq
    seen=set(); uniq=[]
    for p in out:
        if p in seen: continue
        seen.add(p); uniq.append(p)
    return uniq

def has_species_block(text: str, sym: str) -> bool:
    pat = re.compile(rf"\[\s*{re.escape(sym)}\s*\]\s*=\s*\{{", re.M)
    return bool(pat.search(text))

def any_file_mentions(files: List[Path], sym: str) -> bool:
    rx = re.compile(rf"\b{re.escape(sym)}\b")
    for p in files:
        if rx.search(read(p)):
            return True
    return False

def any_file_mentions_shiny(files: List[Path], sym: str) -> bool:
    """
    Very loose: checks the file that mentions the species also contains 'shiny' somewhere.
    This matches the typical pattern where shiny palettes are wired in the same header/table.
    """
    rx = re.compile(rf"\b{re.escape(sym)}\b")
    for p in files:
        t = read(p)
        if rx.search(t) and re.search(r"\bshiny\b", t, re.I):
            return True
    return False

def main() -> int:
    sym_file = REPO / "tools/spaceworld_species_symbols.txt"
    if not sym_file.exists():
        print("ERROR: tools/spaceworld_species_symbols.txt not found. Run the discovery script first.")
        return 2

    syms = [ln.strip() for ln in sym_file.read_text().splitlines() if ln.strip()]
    if not syms:
        print("ERROR: spaceworld_species_symbols.txt is empty.")
        return 2

    buckets = gather_spaceworld_files()
    info_files = find_species_info_sources()

    print(f"Loaded {len(syms)} Spaceworld species symbols.")
    print(f"SpeciesInfo sources: {len(info_files)}")
    print(f"Spaceworld gfx-like files:   {len(buckets['gfx'])}")
    print(f"Spaceworld icon-like files:  {len(buckets['icons'])}")
    print(f"Other spaceworld files:      {len(buckets['other'])}")
    print()

    # Merge gfx search pool: gfx + other (some repos store gfx tables in "other")
    gfx_pool = buckets["gfx"] + buckets["other"]
    icon_pool = buckets["icons"] + buckets["other"]

    rows: List[Row] = []
    # Pre-read speciesinfo once for speed
    info_texts = [(p, read(p)) for p in info_files]

    for sym in syms:
        r = Row(sym=sym)

        # SpeciesInfo block check
        r.species_info_ok = any(has_species_block(t, sym) for _, t in info_texts)
        if not r.species_info_ok:
            r.errors.append("Missing species_info block (gSpeciesInfo entry not found).")

        # Graphics registry mention checks
        r.gfx_mentions = any_file_mentions(gfx_pool, sym)
        if not r.gfx_mentions:
            r.errors.append("No mention of species symbol in any Spaceworld gfx header/table (front/back/pal wiring likely missing).")

        r.icon_mentions = any_file_mentions(icon_pool, sym)
        if not r.icon_mentions:
            r.errors.append("No mention of species symbol in any Spaceworld icon header/table (icon wiring likely missing).")

        r.shiny_mentions = any_file_mentions_shiny(gfx_pool, sym)
        if not r.shiny_mentions:
            # Not fatal; some repos wire shiny elsewhere, but you said every Spaceworld mon *should* have shiny.
            r.errors.append("No obvious 'shiny' wiring found in the gfx file that references this species (shiny palette may be missing/unwired).")

        rows.append(r)

    bad = [r for r in rows if r.errors]

    print("=== Summary ===")
    print(f"Species audited: {len(rows)}")
    print(f"Species with errors: {len(bad)}")
    print()

    # Print the first ~40 failures to keep output readable
    for r in bad[:40]:
        print(f"- {r.sym}")
        for e in r.errors:
            print(f"  ERROR: {e}")
        print()

    if len(bad) > 40:
        print(f"... plus {len(bad) - 40} more with errors")
        print()

    # Exit code: 0 ok, 1 problems
    return 1 if bad else 0

if __name__ == "__main__":
    raise SystemExit(main())
