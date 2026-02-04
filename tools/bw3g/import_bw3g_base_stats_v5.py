#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import re
from datetime import datetime

print("STEP4v5: SCRIPT START", flush=True)

BW3G_ROOT = Path.home() / "decomps/gb/BW3G"
BASE_DIR  = BW3G_ROOT / "data/pokemon/base_stats"
SPECIES_INFO = Path("src/data/pokemon/species_info/bw3g_families.h")

DB_NUM_RE = re.compile(r'^\s*db\s+(\d+)\s*(?:;.*)?$', re.M | re.I)
TYPES_RE  = re.compile(r'^\s*db\s+TYPE_([A-Z0-9_]+)\s*,\s*TYPE_([A-Z0-9_]+)\s*(?:;.*)?$', re.M)
CATCH_RE  = re.compile(r'^\s*db\s+(\d+)\s*;\s*catch\s*rate\s*$', re.M | re.I)
EXP_RE    = re.compile(r'^\s*db\s+(\d+)\s*;\s*(?:base\s*)?exp(?:\s*yield)?\s*$', re.M | re.I)

def parse_base_stats(p: Path) -> dict[str, object]:
    t = p.read_text(encoding="utf-8", errors="ignore")
    out: dict[str, object] = {}

    nums = [int(x) for x in DB_NUM_RE.findall(t)]
    # BW3G appears to use 5 stats: HP, ATK, DEF, SPD, SPECIAL
    if len(nums) >= 5:
        hp, atk, de, spd, special = nums[0], nums[1], nums[2], nums[3], nums[4]
        out.update({"hp": hp, "atk": atk, "def": de, "spd": spd, "sat": special, "sdf": special})

    mt = TYPES_RE.search(t)
    if mt:
        out["type1"], out["type2"] = mt.group(1), mt.group(2)

    mc = CATCH_RE.search(t)
    if mc:
        out["catchRate"] = int(mc.group(1))

    me = EXP_RE.search(t)
    if me:
        out["expYield"] = int(me.group(1))

    return out

def patch_field(body: str, field: str, value: str) -> str:
    pat = re.compile(rf'^(\s*\.{re.escape(field)}\s*=\s*).+?,\s*$', re.M)
    if pat.search(body):
        return pat.sub(rf'\g<1>{value},', body, count=1)
    return body + f"\n    .{field} = {value},"

def main():
    print(f"STEP4v5: BASE_DIR={BASE_DIR} exists={BASE_DIR.exists()}", flush=True)
    print(f"STEP4v5: SPECIES_INFO={SPECIES_INFO} exists={SPECIES_INFO.exists()}", flush=True)
    if not BASE_DIR.exists():
        raise SystemExit(f"STEP4v5 ERROR: missing {BASE_DIR}")
    if not SPECIES_INFO.exists():
        raise SystemExit("STEP4v5 ERROR: bw3g_families.h not found (run from repo root)")

    files = sorted(BASE_DIR.glob("*.asm"))
    print(f"STEP4v5: base_stats files: {len(files)}", flush=True)

    stats = {p.stem.upper(): parse_base_stats(p) for p in files}
    with5 = sum(1 for v in stats.values() if all(k in v for k in ("hp","atk","def","spd","sat","sdf")))
    print(f"STEP4v5: parsed species: {len(stats)} (with mapped 5-stat->6-stat: {with5})", flush=True)

    src = SPECIES_INFO.read_text(encoding="utf-8", errors="ignore")
    bak = SPECIES_INFO.with_suffix(f".h.bak_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    bak.write_text(src, encoding="utf-8")
    print(f"STEP4v5: Backup: {bak}", flush=True)

    block_re = re.compile(r'(\[\s*(SPECIES_[A-Z0-9_]+)\s*\]\s*=\s*\{\s*)(.*?)(\n\s*\}\s*,)', re.S)

    scanned=0
    changed=0
    missing=0
    incomplete=0

    def repl(m: re.Match) -> str:
        nonlocal scanned, changed, missing, incomplete
        scanned += 1
        head, species_token, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)

        name = re.sub(r'^SPECIES_', '', species_token)
        name = re.sub(r'_BW3G$', '', name)
        name = re.sub(r'^BW3G_', '', name)
        name = name.replace('_BW3G_', '_')
        key = name.upper()

        st = stats.get(key)
        if not st:
            missing += 1
            return m.group(0)

        before = body
        if all(k in st for k in ("hp","atk","def","spd","sat","sdf")):
            body = patch_field(body, "baseHP", str(st["hp"]))
            body = patch_field(body, "baseAttack", str(st["atk"]))
            body = patch_field(body, "baseDefense", str(st["def"]))
            body = patch_field(body, "baseSpeed", str(st["spd"]))
            body = patch_field(body, "baseSpAttack", str(st["sat"]))
            body = patch_field(body, "baseSpDefense", str(st["sdf"]))
        else:
            incomplete += 1

        if "type1" in st and "type2" in st:
            body = patch_field(body, "types", f"{{ TYPE_{st['type1']}, TYPE_{st['type2']} }}")
        if "catchRate" in st:
            body = patch_field(body, "catchRate", str(st["catchRate"]))
        if "expYield" in st:
            body = patch_field(body, "expYield", str(st["expYield"]))

        if body != before:
            changed += 1
        return head + body + tail

    SPECIES_INFO.write_text(block_re.sub(repl, src), encoding="utf-8")
    print(f"STEP4v5: blocks scanned: {scanned}", flush=True)
    print(f"STEP4v5: blocks changed: {changed}", flush=True)
    print(f"STEP4v5: blocks missing stats match: {missing}", flush=True)
    print(f"STEP4v5: matched but incomplete: {incomplete}", flush=True)
    print("STEP4v5: DONE", flush=True)

if __name__ == "__main__":
    main()
