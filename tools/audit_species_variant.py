#!/usr/bin/env python3
from pathlib import Path
import re
import sys
from collections import defaultdict

# ---------- config: fields you expect in each species block ----------
WANTED = [
    "baseHP","baseAttack","baseDefense","baseSpeed","baseSpAttack","baseSpDefense",
    "types","catchRate","expYield","evYield",
    "ability1","ability2","hiddenAbility",
    "growthRate","eggGroups","genderRatio","friendship",
    "levelUpLearnset","teachableLearnset","eggMoveLearnset",
    "pokedexNum","categoryName","height","weight","description",
    "footprint","cryId",
    "iconPic","iconPalIndex",
]

# ---------- parsing regex ----------
BLOCK_RE = re.compile(
    r'\[\s*(SPECIES_[A-Z0-9_]+_(?:BW3G|SW|SPACEWORLD))\s*\]\s*=\s*\{(.*?)\n\s*\}\s*,',
    re.S
)
FIELD_RE = re.compile(r'^\s*\.(\w+)\s*=', re.M)

def find_families_file(suffix: str) -> Path:
    """
    Try to locate the families file for the variant.
    Searches src/data/pokemon/species_info/** for something containing the suffix and 'families'.
    """
    root = Path("src/data/pokemon/species_info")
    if not root.exists():
        raise SystemExit(f"Missing directory: {root}")

    suf = suffix.upper()
    candidates = []
    for p in root.rglob("*.h"):
        name = p.name.lower()
        if "families" not in name:
            continue
        text = str(p).lower()
        if suf.lower() in text:
            candidates.append(p)

    # Prefer exact matches if multiple exist
    if not candidates:
        raise SystemExit(
            f"Could not find a *families*.h file containing '{suffix}' under {root}\n"
            f"Tip: pass an explicit path as arg2."
        )

    # If multiple, pick shortest path (usually the canonical one)
    candidates.sort(key=lambda x: (len(str(x)), str(x)))
    return candidates[0]

def audit_file(path: Path, suffix_hint: str, dump_missing_field: str | None = None) -> int:
    txt = path.read_text(encoding="utf-8", errors="ignore")

    blocks = []
    for m in BLOCK_RE.finditer(txt):
        sp = m.group(1)
        body = m.group(2)
        blocks.append((sp, body))

    total = len(blocks)
    print(f"== Audit: {suffix_hint} ==")
    print(f"File: {path}")
    print(f"Species blocks found: {total}\n")

    if total == 0:
        print("ERROR: Found 0 blocks. This usually means:")
        print("  - The file format doesn't match '[SPECIES_X] = { ... },'")
        print("  - The species symbols don't end with _BW3G/_SW/_SPACEWORLD")
        print("  - Or you're auditing the wrong file.\n")
        return 2

    missing_counts = defaultdict(int)
    missing_lists = defaultdict(list)

    for sp, body in blocks:
        fields = set(FIELD_RE.findall(body))
        for w in WANTED:
            if w not in fields:
                missing_counts[w] += 1
                if dump_missing_field == w:
                    missing_lists[w].append(sp)

    # summary
    print("Missing-field counts (how many species blocks lack each field):")
    for k in WANTED:
        print(f"  {k:22s} {missing_counts[k]}")
    print()

    # sanity: show first/last few species symbols found
    species_syms = [sp for sp, _ in blocks]
    print("Species symbol samples:")
    print("  first 5:", ", ".join(species_syms[:5]))
    print("  last  5:", ", ".join(species_syms[-5:]))
    print()

    # optional dump
    if dump_missing_field:
        if dump_missing_field not in WANTED:
            print(f"ERROR: unknown field '{dump_missing_field}'. Valid fields:")
            for k in WANTED:
                print(" ", k)
            return 2
        miss = missing_lists.get(dump_missing_field, [])
        print(f"Species missing field '{dump_missing_field}': {len(miss)}")
        for sp in miss[:200]:
            print(" ", sp)
        if len(miss) > 200:
            print(f"  ... ({len(miss)-200} more)")
        print()

    return 0

def main():
    # Usage:
    #   python3 tools/audit_species_variant.py BW3G
    #   python3 tools/audit_species_variant.py SPACEWORLD
    #   python3 tools/audit_species_variant.py BW3G path/to/file.h
    #   python3 tools/audit_species_variant.py BW3G --dump-missing iconPic
    #
    args = sys.argv[1:]
    if not args:
        print("Usage: python3 tools/audit_species_variant.py <BW3G|SPACEWORLD|SW> [families_file] [--dump-missing FIELD]")
        return 2

    suffix = args[0].upper()

    dump_field = None
    if "--dump-missing" in args:
        i = args.index("--dump-missing")
        if i + 1 >= len(args):
            print("ERROR: --dump-missing requires a FIELD name")
            return 2
        dump_field = args[i + 1]
        # remove these two tokens
        args = args[:i] + args[i+2:]

    families_path = None
    if len(args) >= 2:
        families_path = Path(args[1])
        if not families_path.exists():
            print(f"ERROR: file does not exist: {families_path}")
            return 2
    else:
        families_path = find_families_file(suffix)

    return audit_file(families_path, suffix, dump_missing_field=dump_field)

if __name__ == "__main__":
    raise SystemExit(main())
