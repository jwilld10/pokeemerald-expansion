#!/usr/bin/env python3
from __future__ import annotations
import argparse
import re
from pathlib import Path

def find_first_file_containing(pattern: str, roots: list[Path]) -> Path:
    rx = re.compile(pattern)
    for root in roots:
        for p in root.rglob("*"):
            if p.is_file() and p.suffix in (".c", ".h", ".inc", ".s"):
                try:
                    txt = p.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue
                if rx.search(txt):
                    return p
    raise SystemExit(f"Could not find a file containing pattern: {pattern}")

def extract_species_block(text: str, species: str) -> str:
    pat = re.compile(rf"\[\s*{re.escape(species)}\s*\]\s*=\s*\{{(.*?)\n\}},", re.S)
    m = pat.search(text)
    if not m:
        raise SystemExit(f"Couldn't find species block for {species}")
    return m.group(1)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--suffix", required=True)
    ap.add_argument("--folder", required=True)
    ap.add_argument("--display", required=True)
    args = ap.parse_args()

    base = args.base
    variant = f"{base}_{args.suffix}"

    roots = [Path("src"), Path("include")]
    species_info = find_first_file_containing(r"gSpeciesInfo", roots)

    txt = species_info.read_text(encoding="utf-8", errors="ignore")
    block = extract_species_block(txt, base)

    base_name = base.replace("SPECIES_", "").title().replace("_", "")
    variant_name = base_name + args.suffix

    block = block.replace(base_name, variant_name)

    print("\n// ADD THIS SPECIES DEFINE")
    print(f"#define {variant} <CHOOSE_ID>")

    print("\n// ADD THIS TO gSpeciesInfo")
    print(f"[{variant}] = {{{block}\n}},\n")

    print("\n// GRAPHICS EXTERNS")
    print(f"extern const u32 gMonFrontPic_{variant_name}[];")
    print(f"extern const u32 gMonBackPic_{variant_name}[];")
    print(f"extern const u16 gMonPalette_{variant_name}[];")
    print(f"extern const u16 gMonShinyPalette_{variant_name}[];")
    print(f"extern const u8  gMonIcon_{variant_name}[];")
    print(f"extern const u16 gMonIconPalette_{variant_name}[];")

    print("\n// gSpeciesInfo found in:", species_info)

if __name__ == "__main__":
    main()
