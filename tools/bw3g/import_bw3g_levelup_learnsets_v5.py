#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import re
from datetime import datetime

print("STEP5v5: SCRIPT START", flush=True)

BW3G_ROOT = Path.home() / "decomps/gb/BW3G"
POINTERS  = BW3G_ROOT / "data/pokemon/evos_attacks_pointers.asm"
EVOS      = BW3G_ROOT / "data/pokemon/evos_attacks.asm"

OUT = Path("src/data/pokemon/level_up_learnsets_bw3g.h")
SPECIES_INFO = Path("src/data/pokemon/species_info/bw3g_families.h")
DBG_FILE  = Path("bw3g_levelup_debug.txt")
MISS_FILE = Path("bw3g_levelup_move_misses.txt")

LABEL_RE = re.compile(r'^\s*([A-Za-z0-9_]+)\s*:(?::)?\s*(?:;.*)?$', re.M)

# Lines:
#   db 0 ; no more evolutions
TERM_RE  = re.compile(r'^\s*db\s+0\s*(?:;.*)?$', re.M)

# Move lines:
#   db 16, RAZOR_LEAF ; comment
MOVE_RE  = re.compile(r'^\s*db\s+(\d+)\s*,\s*([A-Z0-9_]+)\s*(?:;.*)?$', re.M)

def load_emerald_moves() -> set[str]:
    for p in (Path("include/constants/moves.h"), Path("include/constants/move.h")):
        if p.exists():
            return set(re.findall(r'\bMOVE_[A-Z0-9_]+\b', p.read_text(encoding="utf-8", errors="ignore")))
    toks=set()
    root = Path("include/constants")
    if root.exists():
        for p in root.rglob("*.h"):
            toks |= set(re.findall(r'\bMOVE_[A-Z0-9_]+\b', p.read_text(encoding="utf-8", errors="ignore")))
    return toks

def parse_pointers(txt: str) -> dict[str, str]:
    out={}
    for line in txt.splitlines():
        raw = line.split(";")[0].strip()
        if not raw:
            continue
        m = re.search(r'\b([A-Za-z0-9_]+EvosAttacks)\b', raw)
        if not m:
            continue
        label = m.group(1)
        mon = re.sub(r'EvosAttacks$', '', label)
        out[mon.upper()] = label
    return out

def index_labels(text: str) -> dict[str, tuple[int,int]]:
    labs = list(LABEL_RE.finditer(text))
    spans={}
    for i,m in enumerate(labs):
        name=m.group(1)
        a=m.end()
        b=labs[i+1].start() if i+1<len(labs) else len(text)
        spans[name]=(a,b)
    return spans

def extract_levelup_moves(block: str) -> list[tuple[int,str]]:
    # Find first evo terminator "db 0"
    m = TERM_RE.search(block)
    if not m:
        return []
    tail = block[m.end():]

    moves=[]
    for line in tail.splitlines():
        if TERM_RE.match(line):
            break
        mm = MOVE_RE.match(line)
        if mm:
            moves.append((int(mm.group(1)), mm.group(2)))
    return moves

def mon_to_c(mon_upper: str) -> str:
    return "".join(p[:1].upper()+p[1:].lower() for p in mon_upper.split("_") if p)

def patch_field(body: str, field: str, value: str) -> str:
    pat = re.compile(rf'^(\s*\.{re.escape(field)}\s*=\s*).+?,\s*$', re.M)
    if pat.search(body):
        return pat.sub(rf'\g<1>{value},', body, count=1)
    return body + f"\n    .{field} = {value},"

def main():
    print(f"STEP5v5: POINTERS exists={POINTERS.exists()}", flush=True)
    print(f"STEP5v5: EVOS exists={EVOS.exists()}", flush=True)
    print(f"STEP5v5: SPECIES_INFO exists={SPECIES_INFO.exists()}", flush=True)

    if not EVOS.exists():
        raise SystemExit(f"STEP5v5 ERROR: missing {EVOS}")

    evostxt = EVOS.read_text(encoding="utf-8", errors="ignore")
    spans = index_labels(evostxt)
    print(f"STEP5v5: labels indexed: {len(spans)}", flush=True)

    ptrs={}
    if POINTERS.exists():
        ptrs = parse_pointers(POINTERS.read_text(encoding="utf-8", errors="ignore"))
    print(f"STEP5v5: pointers parsed: {len(ptrs)}", flush=True)

    # fallback from labels
    if not ptrs:
        for lab in spans.keys():
            if lab.endswith("EvosAttacks"):
                mon = re.sub(r'EvosAttacks$', '', lab)
                ptrs[mon.upper()] = lab
        print(f"STEP5v5: fallback pointers: {len(ptrs)}", flush=True)

    emerald_moves = load_emerald_moves()
    print(f"STEP5v5: Emerald MOVE_* constants detected: {len(emerald_moves)}", flush=True)

    OUT.parent.mkdir(parents=True, exist_ok=True)

    learnset_syms={}
    debug=[]
    missing_moves=set()
    generated=0

    lines=[]
    lines.append("// Auto-generated BW3G level-up learnsets (from evos_attacks.asm)\n")
    lines.append("#pragma once\n")
    lines.append('#include "constants/moves.h"\n')
    lines.append('#include "data/pokemon/level_up_learnsets.h"\n\n')

    for mon_upper, label in sorted(ptrs.items()):
        if label not in spans:
            debug.append(f"NO_LABEL_MATCH mon={mon_upper} label={label}")
            continue

        a,b = spans[label]
        block = evostxt[a:b]
        mv = extract_levelup_moves(block)
        if not mv:
            debug.append(f"NO_MOVES mon={mon_upper} label={label}")
            continue

        cmon = mon_to_c(mon_upper)
        sym = f"s{cmon}LevelUpLearnsetBw3g"
        learnset_syms[mon_upper] = sym
        generated += 1

        lines.append(f"static const u16 {sym}[] = {{\n")
        for lvl, tok in sorted(mv, key=lambda x: x[0]):
            move_sym = "MOVE_" + tok.upper()
            if move_sym not in emerald_moves:
                missing_moves.add(tok.upper())
            lines.append(f"    LEVEL_UP_MOVE({lvl}, {move_sym}),\n")
        lines.append("    LEVEL_UP_END\n};\n\n")

    OUT.write_text("".join(lines), encoding="utf-8")
    DBG_FILE.write_text("\n".join(debug)+("\n" if debug else ""), encoding="utf-8")

    print(f"STEP5v5: Wrote {OUT} (learnsets generated: {generated})", flush=True)
    print(f"STEP5v5: Wrote {DBG_FILE} (debug lines: {len(debug)})", flush=True)

    if missing_moves:
        MISS_FILE.write_text("\n".join(sorted(missing_moves))+"\n", encoding="utf-8")
        print(f"STEP5v5: Wrote {MISS_FILE} (missing MOVE tokens: {len(missing_moves)})", flush=True)
    else:
        print("STEP5v5: No missing MOVE tokens detected", flush=True)

    # Patch species_info
    if not SPECIES_INFO.exists():
        print("STEP5v5: NOTE bw3g_families.h missing; skipping patch.", flush=True)
        return

    src = SPECIES_INFO.read_text(encoding="utf-8", errors="ignore")
    bak = SPECIES_INFO.with_suffix(f".h.bak_learnsets_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    bak.write_text(src, encoding="utf-8")
    print(f"STEP5v5: Backup: {bak}", flush=True)

    block_re = re.compile(r'(\[\s*(SPECIES_[A-Z0-9_]+)\s*\]\s*=\s*\{\s*)(.*?)(\n\s*\}\s*,)', re.S)
    scanned=0
    changed=0

    def repl(m: re.Match) -> str:
        nonlocal scanned, changed
        scanned += 1
        head, species_token, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)

        name = re.sub(r'^SPECIES_', '', species_token)
        name = re.sub(r'_BW3G$', '', name)
        name = re.sub(r'^BW3G_', '', name)
        name = name.replace('_BW3G_', '_')
        key = name.upper()

        sym = learnset_syms.get(key)
        if not sym:
            return m.group(0)

        before = body
        body = patch_field(body, "levelUpLearnset", sym)
        if body != before:
            changed += 1
        return head + body + tail

    SPECIES_INFO.write_text(block_re.sub(repl, src), encoding="utf-8")
    print(f"STEP5v5: blocks scanned: {scanned}", flush=True)
    print(f"STEP5v5: blocks changed: {changed}", flush=True)
    print("STEP5v5: DONE", flush=True)

if __name__ == "__main__":
    main()
