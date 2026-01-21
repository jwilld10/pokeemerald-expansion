#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import shutil
import subprocess
import sys

REPO_ROOT = Path.cwd()
CONV = REPO_ROOT / "tools/spaceworld/convert_spaceworld_pal.py"

def cp(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)

def run(cmd: list[str]) -> None:
    r = subprocess.run(cmd, check=False, text=True, capture_output=True)
    if r.returncode != 0:
        sys.stderr.write(r.stdout)
        sys.stderr.write(r.stderr)
        raise SystemExit(r.returncode)

def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Usage: import_spaceworld_sprites.py /path/to/spaceworld_root", file=sys.stderr)
        return 2

    sw = Path(argv[1]).resolve()
    sw_gfx = sw / "gfx" / "pokemon"
    if not sw_gfx.is_dir():
        print(f"Missing: {sw_gfx}", file=sys.stderr)
        return 1

    out_root = REPO_ROOT / "graphics" / "spaceworld" / "pokemon"
    out_root.mkdir(parents=True, exist_ok=True)

    # Base unown palette files (special case)
    unown_dir = sw_gfx / "unown"
    unown_norm_text = unown_dir / "normal.pal"
    unown_shiny_text = unown_dir / "shiny.pal"

    imported = 0
    missing = []

    for mon_dir in sorted(p for p in sw_gfx.iterdir() if p.is_dir()):
        mon = mon_dir.name  # folder name is truth
        dst = out_root / mon

        front_png = mon_dir / "front.png"
        frontS_png = mon_dir / "front_S.png"
        back_png  = mon_dir / "back.png"

        if not front_png.exists() or not back_png.exists():
            missing.append(mon)
            continue

        # Copy images -> our naming
        cp(front_png, dst / "anim_front.png")
        cp(back_png,  dst / "back.png")

        # Your rule: front_S becomes female front if present
        if frontS_png.exists():
            cp(frontS_png, dst / "anim_frontf.png")

        # Palettes:
        # normal: front.gbcpal for most, but Unown uses normal.pal (text)
        # shiny: shiny.pal (text)
        front_gbcpal = mon_dir / "front.gbcpal"
        shiny_pal    = mon_dir / "shiny.pal"
        normal_pal   = mon_dir / "normal.pal"   # only for unown base in your notes

        if mon == "unown":
            if not normal_pal.exists():
                print("WARNING: unown missing normal.pal; skipping palette", file=sys.stderr)
            else:
                run([str(CONV), str(normal_pal), str(dst / "normal.gbapal")])
            if shiny_pal.exists():
                run([str(CONV), str(shiny_pal), str(dst / "shiny.gbapal")])
        else:
            # If front.gbcpal exists, convert it. If not, and it's an unown variant, use base unown palettes.
            if front_gbcpal.exists():
                run([str(CONV), str(front_gbcpal), str(dst / "normal.gbapal")])
            else:
                # likely unown variants
                if unown_norm_text.exists():
                    run([str(CONV), str(unown_norm_text), str(dst / "normal.gbapal")])
                else:
                    print(f"WARNING: {mon} missing normal palette and base unown normal.pal missing too", file=sys.stderr)

            # shiny
            if shiny_pal.exists():
                run([str(CONV), str(shiny_pal), str(dst / "shiny.gbapal")])
            else:
                # unown variants again
                if unown_shiny_text.exists():
                    run([str(CONV), str(unown_shiny_text), str(dst / "shiny.gbapal")])

        imported += 1

    print(f"Imported sprite PNGs for: {imported} mons")
    if missing:
        print(f"WARNING: missing front/back PNG for {len(missing)} mons. First 30: {missing[:30]}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
