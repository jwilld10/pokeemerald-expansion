#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import re
import sys

def die(msg: str, code: int = 1):
    print(f"ERROR: {msg}", file=sys.stderr)
    raise SystemExit(code)

def read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="ignore")

# BW3G dex entry format:
#   db "CATEGORY@" ; species name
#   dw 200, 179 ; height, weight
#   db "line..."
#   next "line..."
#   page "line..."
#   next "line...@"
#
RE_CAT = re.compile(r'^\s*db\s+"([^"]*)@"\s*;+\s*species name\s*$', re.M)
RE_HW  = re.compile(r'^\s*dw\s*([0-9]+)\s*,\s*([0-9]+)\s*;+\s*height,\s*weight\s*$', re.M)
RE_TEXT_LINE = re.compile(r'^\s*(db|next|page)\s+"([^"]*)"\s*$', re.M)

def sanitize_c_ident(name: str) -> str:
    # Expect lowercase file stem like "mr_mime" or "farfetchd" etc; keep it safe-ish.
    out = re.sub(r'[^A-Za-z0-9_]', '_', name)
    out = re.sub(r'_+', '_', out).strip('_')
    if not out:
        out = "unknown"
    return out

def to_c_string(s: str) -> str:
    # Escape for C string literal
    s = s.replace("\\", "\\\\").replace('"', '\\"')
    return s

def parse_entry_file(p: Path) -> dict:
    txt = read_text(p)

    mcat = RE_CAT.search(txt)
    if not mcat:
        die(f"missing category line in {p}")
    category = mcat.group(1)

    mhw = RE_HW.search(txt)
    if not mhw:
        die(f"missing height/weight line in {p}")
    height = int(mhw.group(1))
    weight = int(mhw.group(2))

    # Collect text lines in order. 'page' becomes blank line between pages.
    lines: list[str] = []
    for m in RE_TEXT_LINE.finditer(txt):
        kind, frag = m.group(1), m.group(2)

        # remove trailing '@' if present in final fragment
        if frag.endswith("@"):
            frag = frag[:-1]

        frag = frag.rstrip()

        if kind == "page":
            # page break: blank line between pages
            if lines and lines[-1] != "":
                lines.append("")
            lines.append(frag)
        else:
            lines.append(frag)

    # Clean: join into two pages with '\n', and compress obvious double spaces.
    # Also trim each line.
    cleaned = []
    for ln in lines:
        cleaned.append(ln.strip())

    # Remove leading/trailing blank lines
    while cleaned and cleaned[0] == "":
        cleaned.pop(0)
    while cleaned and cleaned[-1] == "":
        cleaned.pop()

    # Some entries have intentional trailing spaces before page; normalize internal multiple spaces.
    out_lines = [re.sub(r'\s{2,}', ' ', ln) for ln in cleaned]
    description = "\\n".join(out_lines)

    return {
        "category": category,
        "height": height,
        "weight": weight,
        "description": description,
    }

def find_include_order(dex_entries_asm: Path) -> list[tuple[str, Path]]:
    # Returns list of (MonNamePascal, entry_file_path) in include order.
    # Example line: SnivyPokedexEntry::   INCLUDE "data/pokemon/dex_entries/snivy.asm"
    txt = read_text(dex_entries_asm)
    inc_re = re.compile(r'^\s*([A-Za-z0-9]+)PokedexEntry::\s+INCLUDE\s+"(data/pokemon/dex_entries/[^"]+\.asm)"\s*$', re.M)
    out = []
    for m in inc_re.finditer(txt):
        mon = m.group(1)  # PascalCase-ish
        rel = m.group(2)
        out.append((mon, dex_entries_asm.parent.parent.parent / rel))  # ROOT/data/pokemon/... from ROOT/data/pokemon/dex_entries.asm
    return out

def ensure_include_in_bw3g_families(bw3g_families_h: Path, include_line: str) -> None:
    txt = read_text(bw3g_families_h)

    if include_line in txt:
        return

    # Insert after guard define (or after initial comment/guard block).
    # Find first "#define GUARD_..." and insert after it.
    m = re.search(r'^\s*#define\s+GUARD_[A-Z0-9_]+\s*$', txt, re.M)
    if not m:
        die(f"could not find header guard #define in {bw3g_families_h}")

    insert_pos = m.end()
    new_txt = txt[:insert_pos] + "\n" + include_line + "\n" + txt[insert_pos:]
    bw3g_families_h.write_text(new_txt, encoding="utf-8")

def patch_bw3g_families_descriptions_and_nums(bw3g_families_h: Path, mapping: dict[str, dict], order: list[str]) -> None:
    """
    For each [SPECIES_<MON>_BW3G] block:
      - add .description if missing
      - add .pokedexNum if missing
    Uses include order as pokedexNum (1..253).
    """
    txt = read_text(bw3g_families_h)

    # Build mon->dexnum from order
    dexnum = {}
    for i, mon in enumerate(order, start=1):
        dexnum[mon] = i

    # Find blocks:
    #   [SPECIES_SNIVY_BW3G] =
    #   {
    #       ...
    #   },
    start_re = re.compile(r'^\s*\[\s*(SPECIES_([A-Z0-9_]+)_BW3G)\s*\]\s*=\s*$', re.M)

    starts = [(m.start(), m.end(), m.group(1), m.group(2)) for m in start_re.finditer(txt)]
    if not starts:
        die(f"no BW3G species entries found in {bw3g_families_h}")

    out = []
    last = 0
    patched = 0

    for idx, (s, e, full_species_sym, mon_sym) in enumerate(starts):
        block_end = starts[idx+1][0] if idx+1 < len(starts) else len(txt)
        block = txt[e:block_end]

        # Only patch if we have a dex entry for it
        mon_key = mon_sym.title()  # not reliable for underscores, so use mapping keys we create below
        # We'll key mapping by MON symbol (the part after SPECIES_ and before _BW3G)
        if mon_sym not in mapping:
            # Keep block unchanged
            out.append(txt[last:block_end])
            last = block_end
            continue

        want_desc = f"gBw3gPokedexText_{mapping[mon_sym]['mon_pascal']}"
        want_num = dexnum.get(mapping[mon_sym]["mon_pascal"], None)

        # Check if fields exist
        has_desc = re.search(r'^\s*\.description\s*=\s*', block, re.M) is not None
        has_num  = re.search(r'^\s*\.pokedexNum\s*=\s*', block, re.M) is not None

        if has_desc and has_num:
            out.append(txt[last:block_end])
            last = block_end
            continue

        # Insert near end of block, right before closing "}," line (indented).
        # Find last occurrence of a line that looks like "    }," inside this slice.
        mclose = re.search(r'^\s*\},\s*$', block, re.M)
        if not mclose:
            # if formatting differs, just leave it untouched
            out.append(txt[last:block_end])
            last = block_end
            continue

        insert_at = mclose.start()

        ins_lines = ""
        if not has_num and want_num is not None:
            ins_lines += f"        .pokedexNum = {want_num},\n"
        if not has_desc:
            ins_lines += f"        .description = {want_desc},\n"

        new_block = block[:insert_at] + ins_lines + block[insert_at:]
        out.append(txt[last:e] + new_block)
        last = block_end
        patched += 1

    new_txt = "".join(out)
    bw3g_families_h.write_text(new_txt, encoding="utf-8")
    print(f"Patched {bw3g_families_h} (updated {patched} entries)")

def main():
    if len(sys.argv) != 4:
        print("Usage: import_bw3g_dex_to_emerald.py <BW3G_ROOT> <bw3g_families.h> <out_header.h>", file=sys.stderr)
        raise SystemExit(2)

    bw3g_root = Path(sys.argv[1]).expanduser()
    families_h = Path(sys.argv[2])
    out_header = Path(sys.argv[3])

    dex_entries_asm = bw3g_root / "data/pokemon/dex_entries.asm"
    dex_dir = bw3g_root / "data/pokemon/dex_entries"

    if not dex_entries_asm.exists():
        die(f"missing {dex_entries_asm}")
    if not dex_dir.is_dir():
        die(f"missing {dex_dir}")

    include_order = find_include_order(dex_entries_asm)
    if not include_order:
        die(f"no includes found in {dex_entries_asm}")

    # Parse all entries
    entries = []
    mapping_by_mon_sym = {}  # "SNIVY" -> {mon_pascal:"Snivy", ...}
    for mon_pascal, entry_path in include_order:
        if not entry_path.exists():
            die(f"include points to missing file: {entry_path}")

        data = parse_entry_file(entry_path)

        # Convert mon_pascal to the species symbol part used in bw3g_families: usually uppercase with underscores.
        # Example: Snivy -> SNIVY.  MrMime -> MR_MIME (unknown here). We'll derive from filename stem instead.
        stem = entry_path.stem  # e.g. snivy
        mon_sym = stem.upper()
        mon_sym = mon_sym.replace("-", "_")
        mon_sym = mon_sym.replace("'", "")
        mon_sym = mon_sym.replace(".", "_")
        mon_sym = mon_sym.replace("__", "_")

        mapping_by_mon_sym[mon_sym] = {
            "mon_pascal": mon_pascal,
            "file": str(entry_path),
            "category": data["category"],
            "height": data["height"],
            "weight": data["weight"],
            "description": data["description"],
        }
        entries.append((mon_pascal, mon_sym, data))

    # Write output header
    out_header.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    lines.append("// Auto-generated: BW3G dex text import")
    lines.append("#ifndef GUARD_BW3G_POKEDEX_TEXT_H")
    lines.append("#define GUARD_BW3G_POKEDEX_TEXT_H")
    lines.append("")
    lines.append("#include \"global.h\"")
    lines.append("")

    for mon_pascal, mon_sym, data in entries:
        desc = to_c_string(data["description"])
        # Use two-line string literal style for easier diffs; keep \n escapes as-is.
        lines.append(f"static const u8 gBw3gPokedexText_{mon_pascal}[] = _(\"{desc}\");")

    lines.append("")
    lines.append("#endif // GUARD_BW3G_POKEDEX_TEXT_H")
    out_header.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {out_header} ({len(entries)} entries)")

    # Ensure include in bw3g_families.h and patch fields
    include_line = '#include "data/pokemon/bw3g_generated/bw3g_pokedex_text.h"'
    ensure_include_in_bw3g_families(families_h, include_line)

    # Patch .pokedexNum and .description into each block
    order_pascal = [mon_pascal for mon_pascal, _ in include_order]
    patch_bw3g_families_descriptions_and_nums(families_h, mapping_by_mon_sym, order_pascal)

if __name__ == "__main__":
    main()
