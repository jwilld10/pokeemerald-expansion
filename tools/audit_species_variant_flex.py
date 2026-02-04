#!/usr/bin/env python3
from pathlib import Path
import re
import sys
from collections import defaultdict

WANTED = [
    "baseHP","baseAttack","baseDefense","baseSpeed","baseSpAttack","baseSpDefense",
    "types","catchRate","expYield","evYield",
    "ability1","ability2","hiddenAbility",
    "growthRate","eggGroups","genderRatio","friendship",
    "levelUpLearnset","teachableLearnset","eggMoveLearnset",
    "pokedexNum","categoryName","height","weight","description",
    "footprint","cryId",
    "iconSprite","iconPalIndex",
    "frontPic",
]

def main():
    if len(sys.argv) < 3:
        print("Usage: audit_species_variant_flex.py <TAG> <file.h>")
        return 2

    tag = sys.argv[1]
    path = Path(sys.argv[2])
    if not path.exists():
        print(f"Missing {path}")
        return 1

    txt = path.read_text(encoding="utf-8", errors="ignore")

    # Match the exact style you have:
    #   [SPECIES_X_TAG] =
    #   {
    entry_start = re.compile(
        r'^\s*\[\s*(SPECIES_[A-Z0-9_]+_' + re.escape(tag) + r')\s*\]\s*=\s*$',
        re.M
    )

    # Also tolerate: [SPECIES_X_TAG] = {   (just in case other files differ)
    entry_start_brace = re.compile(
        r'^\s*\[\s*(SPECIES_[A-Z0-9_]+_' + re.escape(tag) + r')\s*\]\s*=\s*\{',
        re.M
    )

    field_re = re.compile(r'^\s*\.(\w+)\s*=', re.M)

    starts_map = {}

    for m in entry_start.finditer(txt):
        starts_map.setdefault(m.group(1), (m.start(), m.end(), m.group(1)))
    for m in entry_start_brace.finditer(txt):
        starts_map.setdefault(m.group(1), (m.start(), m.end(), m.group(1)))

    starts = sorted(starts_map.values(), key=lambda t: t[0])

    print(f"== Audit: {tag} ==")
    print(f"File: {path}")

    if not starts:
        print("No entries found.")
        return 1

    missing_counts = defaultdict(int)
    total = 0

    for i, (spos, epos, sym) in enumerate(starts):
        block_start = epos
        block_end = starts[i+1][0] if i+1 < len(starts) else len(txt)
        body = txt[block_start:block_end]

        fields = set(field_re.findall(body))
        total += 1
        for w in WANTED:
            if w not in fields:
                missing_counts[w] += 1

    print(f"Entries found: {total}\n")
    print("Missing-field counts (how many entries lack each field):")
    for k in WANTED:
        print(f"  {k:22s} {missing_counts[k]}")

    print("\nSpecies symbol samples:")
    print("  first 5:", ", ".join([s[2] for s in starts[:5]]))
    print("  last  5:", ", ".join([s[2] for s in starts[-5:]]))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
