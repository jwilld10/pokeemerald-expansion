#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import re
from datetime import datetime

ROOT = Path(".")
TYPES_INFO = ROOT / "src/data/types_info.h"
MOVES_CONST = ROOT / "include/constants/moves.h"
MOVES_INFO = ROOT / "src/data/moves_info.h"
ALIASES_HDR = ROOT / "include/constants/moves_bw3g_aliases.h"
BW3G_FAM = ROOT / "src/data/pokemon/species_info/bw3g_families.h"

STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

def backup(p: Path) -> Path:
    b = p.with_suffix(p.suffix + f".bak_{STAMP}")
    b.write_text(p.read_text(encoding="utf-8", errors="ignore"), encoding="utf-8")
    return b

def ensure_types_info_display_unknown() -> None:
    if not TYPES_INFO.exists():
        print(f"[WARN] Missing {TYPES_INFO}; skipping type name display patch.")
        return
    txt = TYPES_INFO.read_text(encoding="utf-8", errors="ignore")
    bak = backup(TYPES_INFO)
    changed = False

    # Common pattern in pokeemerald-expansion:
    # [TYPE_FAIRY] = { .name = _("FAIRY"), ... }
    block_re = re.compile(r'(\[\s*TYPE_FAIRY\s*\]\s*=\s*\{\s*)(.*?)(\n\s*\}\s*,)', re.S)
    m = block_re.search(txt)
    if m:
        head, body, tail = m.group(1), m.group(2), m.group(3)
        # Replace .name = _("FAIRY") or similar with "???"
        body2 = re.sub(r'(\.name\s*=\s*_\(")[^"]*("\)\s*,)', r'\1???\2', body, count=1)
        if body2 != body:
            txt = txt[:m.start()] + head + body2 + tail + txt[m.end():]
            changed = True
    else:
        # Fallback: replace a type name table entry "FAIRY" -> "???"
        # (kept conservative: only the first occurrence)
        txt2 = re.sub(r'_\("FAIRY"\)', '_("???")', txt, count=1)
        if txt2 != txt:
            txt = txt2
            changed = True

    if changed:
        TYPES_INFO.write_text(txt, encoding="utf-8")
        print(f"[OK] TYPE_FAIRY display renamed to '???' in {TYPES_INFO} (backup: {bak})")
    else:
        print(f"[OK] No changes needed in {TYPES_INFO} (already patched or layout differs).")

def detect_move_symbol(preferred: str, candidates: list[str]) -> str|None:
    if not MOVES_CONST.exists():
        return None
    t = MOVES_CONST.read_text(encoding="utf-8", errors="ignore")
    # moves.h usually contains enum tokens MOVE_...
    for sym in candidates:
        if re.search(rf'\b{re.escape(sym)}\b', t):
            return sym
    return None

def ensure_bw3g_move_aliases() -> None:
    # BW3G tokens are DAZZLINGLEAM / DRAININGKISS (no underscore).
    # We try to map them to existing repo move IDs first:
    # - MOVE_DAZZLING_GLEAM (common)
    # - MOVE_DRAINING_KISS (common)
    # If not present, we fall back to "good enough" stand-ins, but we print a warning.
    dazz = detect_move_symbol("MOVE_DAZZLING_GLEAM", ["MOVE_DAZZLING_GLEAM", "MOVE_DAZZLINGGLEAM", "MOVE_DAZZLINGLEAM"])
    kiss = detect_move_symbol("MOVE_DRAINING_KISS", ["MOVE_DRAINING_KISS", "MOVE_DRAININGKISS"])

    fallback_dazz = "MOVE_SWIFT"
    fallback_kiss = "MOVE_MEGA_DRAIN"

    lines = []
    lines.append("#pragma once\n")
    lines.append("// Auto-generated BW3G move aliases.\n")
    lines.append("// BW3G learnsets use tokens DAZZLINGLEAM and DRAININGKISS.\n")
    lines.append("// We keep Fairy mechanics under TYPE_FAIRY, but display it as '???'.\n\n")

    if dazz:
        lines.append(f"#define MOVE_DAZZLINGLEAM {dazz}\n")
        print(f"[OK] Mapping BW3G DAZZLINGLEAM -> {dazz}")
    else:
        lines.append(f"#define MOVE_DAZZLINGLEAM {fallback_dazz}\n")
        print(f"[WARN] No Dazzling Gleam move ID found in include/constants/moves.h; falling back to {fallback_dazz}")

    if kiss:
        lines.append(f"#define MOVE_DRAININGKISS {kiss}\n")
        print(f"[OK] Mapping BW3G DRAININGKISS -> {kiss}")
    else:
        lines.append(f"#define MOVE_DRAININGKISS {fallback_kiss}\n")
        print(f"[WARN] No Draining Kiss move ID found in include/constants/moves.h; falling back to {fallback_kiss}")

    ALIASES_HDR.parent.mkdir(parents=True, exist_ok=True)
    if ALIASES_HDR.exists():
        bak = backup(ALIASES_HDR)
        print(f"[OK] Backed up existing {ALIASES_HDR} -> {bak}")
    ALIASES_HDR.write_text("".join(lines), encoding="utf-8")
    print(f"[OK] Wrote {ALIASES_HDR}")

    # Ensure the BW3G learnset header includes this aliases header
    learn_hdr = ROOT / "src/data/pokemon/level_up_learnsets_bw3g.h"
    if learn_hdr.exists():
        txt = learn_hdr.read_text(encoding="utf-8", errors="ignore")
        inc = '#include "constants/moves_bw3g_aliases.h"\n'
        if inc not in txt:
            bak2 = backup(learn_hdr)
            txt2 = re.sub(r'(#include\s+"constants/moves\.h"\s*\n)', r'\1' + inc, txt, count=1)
            if txt2 == txt:
                txt2 = inc + txt
            learn_hdr.write_text(txt2, encoding="utf-8")
            print(f"[OK] Patched {learn_hdr} to include aliases header (backup: {bak2})")
        else:
            print(f"[OK] {learn_hdr} already includes aliases header")
    else:
        print(f"[WARN] Missing {learn_hdr}; cannot auto-include aliases header (but aliases header still written).")

def patch_distorted_unova_fairy_types() -> None:
    if not BW3G_FAM.exists():
        print(f"[WARN] Missing {BW3G_FAM}; skipping distorted typing patch.")
        return

    # Distorted-only: apply TYPE_FAIRY (displayed as ???) to BW3G incarnations of fairy-converted mons.
    # Mapping is based on *final Fairy typings* but only applied to _BW3G variants (incarnation-tied).
    # (You can expand this list later.)
    FAIRY_MAP = {
        # line heads / singletons
        "CLEFAIRY": ("TYPE_FAIRY", "TYPE_FAIRY"),
        "CLEFABLE": ("TYPE_FAIRY", "TYPE_FAIRY"),
        "JIGGLYPUFF": ("TYPE_NORMAL", "TYPE_FAIRY"),
        "WIGGLYTUFF": ("TYPE_NORMAL", "TYPE_FAIRY"),
        "TOGEPI": ("TYPE_FAIRY", "TYPE_FAIRY"),
        "TOGETIC": ("TYPE_FAIRY", "TYPE_FLYING"),
        "TOGEKISS": ("TYPE_FAIRY", "TYPE_FLYING"),
        "MARILL": ("TYPE_WATER", "TYPE_FAIRY"),
        "AZUMARILL": ("TYPE_WATER", "TYPE_FAIRY"),
        "SNUBBULL": ("TYPE_FAIRY", "TYPE_FAIRY"),
        "GRANBULL": ("TYPE_FAIRY", "TYPE_FAIRY"),
        "RALTS": ("TYPE_PSYCHIC", "TYPE_FAIRY"),
        "KIRLIA": ("TYPE_PSYCHIC", "TYPE_FAIRY"),
        "GARDEVOIR": ("TYPE_PSYCHIC", "TYPE_FAIRY"),
        "MAWILE": ("TYPE_STEEL", "TYPE_FAIRY"),
        "MR_MIME": ("TYPE_PSYCHIC", "TYPE_FAIRY"),
        "MIME_JR": ("TYPE_PSYCHIC", "TYPE_FAIRY"),
        "COTTONEE": ("TYPE_GRASS", "TYPE_FAIRY"),
        "WHIMSICOTT": ("TYPE_GRASS", "TYPE_FAIRY"),
    }

    txt = BW3G_FAM.read_text(encoding="utf-8", errors="ignore")
    bak = backup(BW3G_FAM)

    block_re = re.compile(r'(\[\s*(SPECIES_[A-Z0-9_]+)\s*\]\s*=\s*\{\s*)(.*?)(\n\s*\}\s*,)', re.S)

    scanned=0
    changed=0

    def repl(m: re.Match) -> str:
        nonlocal scanned, changed
        scanned += 1
        head, species_token, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)

        # Only touch BW3G incarnations
        if not species_token.endswith("_BW3G"):
            return m.group(0)

        base = re.sub(r'^SPECIES_', '', species_token)
        base = re.sub(r'_BW3G$', '', base)
        base = re.sub(r'^BW3G_', '', base)

        if base not in FAIRY_MAP:
            return m.group(0)

        t1, t2 = FAIRY_MAP[base]
        before = body

        # Replace existing .types = { ... } if present; else append.
        types_pat = re.compile(r'^(\s*\.types\s*=\s*)\{[^}]*\}\s*,\s*$', re.M)
        if types_pat.search(body):
            body = types_pat.sub(rf'\1{{ {t1}, {t2} }},', body, count=1)
        else:
            body = body + f"\n    .types = {{ {t1}, {t2} }},"

        if body != before:
            changed += 1

        return head + body + tail

    out = block_re.sub(repl, txt)
    BW3G_FAM.write_text(out, encoding="utf-8")

    print(f"[OK] Patched distorted Unova typing in {BW3G_FAM} (backup: {bak})")
    print(f"[OK] blocks scanned: {scanned}")
    print(f"[OK] blocks changed: {changed}")
    if changed == 0:
        print("[NOTE] No BW3G species matched the fairy-map list. If your BW3G tokens differ (e.g. MR__MIME), we can adapt the map.")

def main():
    ensure_types_info_display_unknown()
    ensure_bw3g_move_aliases()
    patch_distorted_unova_fairy_types()
    print("[DONE] Unova anomaly (???/Fairy) setup complete.")
    print("Next: run `make -j$(nproc)` and paste any compiler errors if they appear.")

if __name__ == "__main__":
    main()
