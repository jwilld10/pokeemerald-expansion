#!/usr/bin/env bash
set -euo pipefail

# Reimport Spaceworld summary sprites with filename mapping:
#   front.png   -> anim_front.png
#   front_S.png -> anim_frontf.png

SRC_ROOT="${1:-}"
shift || true

RESTORE_GIT=0
EXCLUDE_ZUBAT_MALE=0
DRY_RUN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --restore-git) RESTORE_GIT=1 ;;
    --exclude-zubat-male) EXCLUDE_ZUBAT_MALE=1 ;;
    --dry-run) DRY_RUN=1 ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
  shift
done

if [[ -z "$SRC_ROOT" || ! -d "$SRC_ROOT" ]]; then
  echo "ERROR: valid Spaceworld repo path required" >&2
  exit 1
fi

DST_ROOT="graphics/spaceworld/pokemon"

ts="$(date +%Y%m%d_%H%M%S)"
backup="graphics/spaceworld/pokemon_backup_before_reimport_${ts}"

echo "== Backup destination → $backup"
if [[ "$DRY_RUN" == "0" ]]; then
  cp -a "$DST_ROOT" "$backup"
fi

if [[ "$RESTORE_GIT" == "1" ]]; then
  echo "== Restoring graphics/spaceworld/pokemon from git"
  if [[ "$DRY_RUN" == "0" ]]; then
    git restore -- graphics/spaceworld/pokemon || true
  fi
fi

python3 - <<'PY' "$SRC_ROOT" "$DST_ROOT" "$EXCLUDE_ZUBAT_MALE" "$DRY_RUN"
import os, sys, shutil

src_root, dst_root = sys.argv[1], sys.argv[2]
exclude_zubat_male = sys.argv[3] == "1"
dry_run = sys.argv[4] == "1"

copied = skipped = 0

for dirpath, _, files in os.walk(src_root):
    if "front.png" not in files:
        continue

    species = os.path.basename(dirpath)
    dst_dir = os.path.join(dst_root, species)
    if not os.path.isdir(dst_dir):
        skipped += 1
        continue

    # Male
    if not (exclude_zubat_male and species == "zubat"):
        src = os.path.join(dirpath, "front.png")
        dst = os.path.join(dst_dir, "anim_front.png")
        if dry_run:
            print(f"[DRY] {src} → {dst}")
        else:
            shutil.copy2(src, dst)
        copied += 1

    # Female
    if "front_S.png" in files:
        src = os.path.join(dirpath, "front_S.png")
        dst = os.path.join(dst_dir, "anim_frontf.png")
        if dry_run:
            print(f"[DRY] {src} → {dst}")
        else:
            shutil.copy2(src, dst)
        copied += 1

print(f"\nCopied {copied} PNGs")
print(f"Skipped {skipped} species (no destination folder)")
PY

echo "== Reimport complete"
