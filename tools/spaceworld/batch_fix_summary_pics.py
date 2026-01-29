#!/usr/bin/env python3
import argparse
import os
import sys
import time
import inspect
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

def iter_targets(root: Path):
    for p in root.rglob("anim_front.png"):
        yield p
    for p in root.rglob("anim_frontf.png"):
        yield p

def call_fixer(fixer, png_path: str, do_apply: bool) -> bool:
    """
    Call the underlying fixer in the most compatible way.
    Returns True if it *claims* it changed something, False otherwise.
    """
    # Preferred: explicit per-file function
    for fn_name in ("process_one", "process", "fix_one", "run_one"):
        fn = getattr(fixer, fn_name, None)
        if callable(fn):
            try:
                sig = inspect.signature(fn)
                kwargs = {}
                if "apply" in sig.parameters:
                    kwargs["apply"] = do_apply
                return bool(fn(png_path, **kwargs))
            except TypeError:
                # try simplest form
                return bool(fn(png_path))

    # Fallback: main(png_path, ...)
    main_fn = getattr(fixer, "main", None)
    if callable(main_fn):
        sig = inspect.signature(main_fn)
        params = sig.parameters

        # Build kwargs only if the function supports them
        kwargs = {}
        if "apply" in params:
            kwargs["apply"] = do_apply
        if "do_apply" in params:
            kwargs["do_apply"] = do_apply
        if "write" in params:
            kwargs["write"] = do_apply

        # Some scripts accept dry_run instead of apply
        if "dry_run" in params and "apply" not in params and "do_apply" not in params and "write" not in params:
            kwargs["dry_run"] = (not do_apply)

        # First arg is required path
        out = main_fn(png_path, **kwargs)
        return bool(out) if out is not None else False

    raise RuntimeError("Could not find a callable entrypoint (process/process_one/main) in fixer module")

def main():
    ap = argparse.ArgumentParser(description="Batch-fix Spaceworld summary pics (front + frontf) in one process to avoid WSL crashes.")
    ap.add_argument("--root", default="graphics/spaceworld/pokemon", help="Root directory to scan")
    ap.add_argument("--apply", action="store_true", help="Actually write changes")
    ap.add_argument("--dry-run", action="store_true", help="Do not write (overrides --apply)")
    ap.add_argument("--limit", type=int, default=0, help="Process only N files (0 = all)")
    ap.add_argument("--sleep", type=float, default=0.002, help="Sleep seconds between files")
    ap.add_argument("--sync-every", type=int, default=200, help="Call os.sync() every N files (0 disables)")
    ap.add_argument("--progress-every", type=int, default=50, help="Print progress every N files")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    if not root.exists():
        print(f"ERROR: root not found: {root}", file=sys.stderr)
        return 2

    try:
        import fix_summary_pic_strip_edge_bg_and_center as fixer
    except Exception as e:
        print("ERROR: Could not import tools/spaceworld/fix_summary_pic_strip_edge_bg_and_center.py", file=sys.stderr)
        print(f"Reason: {e}", file=sys.stderr)
        return 3

    do_apply = bool(args.apply) and not bool(args.dry_run)

    files = sorted(iter_targets(root))
    if args.limit and args.limit > 0:
        files = files[:args.limit]
    total = len(files)

    if total == 0:
        print("No anim_front.png / anim_frontf.png files found.")
        return 0

    print(f"Batch fixing {total} files under: {root}")
    print(f"Mode: {'APPLY' if do_apply else 'DRY-RUN'}")

    changed = 0
    for i, p in enumerate(files, 1):
        try:
            did_change = call_fixer(fixer, str(p), do_apply)
            if did_change:
                changed += 1
        except KeyboardInterrupt:
            print("\nInterrupted.")
            break
        except Exception as e:
            print(f"ERROR: {p} :: {e}", file=sys.stderr)

        if args.sleep > 0:
            time.sleep(args.sleep)

        if args.sync_every and args.sync_every > 0 and (i % args.sync_every == 0):
            try:
                os.sync()
            except Exception:
                pass

        if args.progress_every and (i % args.progress_every == 0):
            print(f"... {i}/{total} processed (changed {changed})")

    print(f"Done. Processed {min(i, total)}/{total}. Changed: {changed}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
