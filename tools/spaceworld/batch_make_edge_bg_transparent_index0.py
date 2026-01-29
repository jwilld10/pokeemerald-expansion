#!/usr/bin/env python3
from __future__ import annotations
import os, sys, subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
POKE_ROOT = REPO / "graphics/spaceworld/pokemon"
EXCLUDE = { str(POKE_ROOT / "zubat/anim_front.png") }  # keep zubat male untouched

# Call the existing script, but from ONE python process overall (less WSL stress).
SCRIPT = REPO / "tools/spaceworld/make_edge_bg_transparent_dedicated_index.py"

def run_one(p: Path) -> tuple[int, str]:
    if str(p) in EXCLUDE:
        return (0, f"SKIP: {p} (excluded)\n")

    # Run the existing tool as a subprocess (still one-at-a-time, no xargs fanout)
    # Add --to-index0 and --apply exactly like you were doing.
    cp = subprocess.run(
        ["python3", "-u", str(SCRIPT), str(p), "--apply", "--to-index0"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=str(REPO),
        env=dict(os.environ),
    )
    return (cp.returncode, cp.stdout)

def main() -> int:
    if not POKE_ROOT.exists():
        print(f"ERROR: not found: {POKE_ROOT}", file=sys.stderr)
        return 2

    # Collect targets
    targets = []
    for name in ("anim_front.png", "anim_frontf.png"):
        targets += sorted(POKE_ROOT.rglob(name))

    log = REPO / "spaceworld_batch_fix.log"
    changed = 0
    processed = 0
    failed = 0

    with log.open("w", encoding="utf-8") as f:
        f.write(f"Batch fixing {len(targets)} files under: {POKE_ROOT}\n")
        f.write("Mode: APPLY\n\n")

        for i, p in enumerate(targets, 1):
            processed += 1
            # Throttle + reduce output pressure
            if i % 25 == 0:
                f.flush()

            code, out = run_one(p)
            if code != 0:
                failed += 1
                f.write(f"ERROR: {p}\n{out}\n")
                continue

            # Detect actual file change (fast + reliable)
            # If the tool decided "nothing to do", git diff will be empty.
            diff = subprocess.run(
                ["git", "diff", "--name-only", "--", str(p.relative_to(REPO))],
                cwd=str(REPO),
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
            ).stdout.strip()

            if diff:
                changed += 1
                f.write(f"APPLIED: {p}\n{out}\n")
            else:
                f.write(f"OK(no-change): {p}\n{out}\n")

    print(f"Done. processed={processed} changed={changed} failed={failed}")
    print(f"Log: {log}")
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    raise SystemExit(main())
