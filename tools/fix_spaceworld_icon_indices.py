#!/usr/bin/env python3
"""
Spaceworld icon index normalizer (v2): outline detection via sprite boundary, not canvas edge.

Normalizes per-frame:
  outline -> 2
  fill    -> 1
  accent  -> 3 (optional)

Never touches:
  0 (transparent)
  4 (cream)

Skips ambiguous cases conservatively.
"""

from __future__ import annotations
import argparse
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from collections import Counter
from typing import List, Optional, Tuple


# --- 4bpp decode/encode helpers (GBA tile order) ---

def decode_4bpp_32x32(frame_bytes: bytes) -> List[List[int]]:
    if len(frame_bytes) != 512:
        raise ValueError(f"Expected 512 bytes, got {len(frame_bytes)}")

    img = [[0]*32 for _ in range(32)]
    offset = 0
    for tile_y in range(4):
        for tile_x in range(4):
            tile = frame_bytes[offset:offset+32]
            offset += 32
            for row in range(8):
                row_bytes = tile[row*4:(row+1)*4]
                for col_pair in range(4):
                    b = row_bytes[col_pair]
                    lo = b & 0x0F
                    hi = (b >> 4) & 0x0F
                    x = tile_x*8 + col_pair*2
                    y = tile_y*8 + row
                    img[y][x] = lo
                    img[y][x+1] = hi
    return img

def encode_4bpp_32x32(img: List[List[int]]) -> bytes:
    out = bytearray()
    for tile_y in range(4):
        for tile_x in range(4):
            tile_bytes = bytearray(32)
            for row in range(8):
                for col_pair in range(4):
                    x = tile_x*8 + col_pair*2
                    y = tile_y*8 + row
                    lo = img[y][x] & 0x0F
                    hi = img[y][x+1] & 0x0F
                    tile_bytes[row*4 + col_pair] = lo | (hi << 4)
            out.extend(tile_bytes)
    return bytes(out)


def split_frames(data: bytes) -> List[bytes]:
    if len(data) == 512:
        return [data]
    if len(data) == 1024:
        return [data[:512], data[512:]]
    return []


# --- boundary-based role detection ---

def in_bounds(x: int, y: int) -> bool:
    return 0 <= x < 32 and 0 <= y < 32

def boundary_pixels(img: List[List[int]]) -> List[int]:
    """
    Boundary pixels = non-transparent pixels that touch transparency (4-neighborhood).
    This captures the sprite outline even if it's centered.
    """
    vals = []
    for y in range(32):
        for x in range(32):
            v = img[y][x]
            if v == 0:
                continue
            # if any 4-neighbor is transparent, treat as boundary
            for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
                nx, ny = x+dx, y+dy
                if in_bounds(nx, ny):
                    if img[ny][nx] == 0:
                        vals.append(v)
                        break
                else:
                    # outside image counts as transparent
                    vals.append(v)
                    break
    return vals

def interior_pixels(img: List[List[int]]) -> List[int]:
    """
    Interior pixels = non-transparent pixels not on boundary.
    Used to find fill/accent.
    """
    bset = set()
    for y in range(32):
        for x in range(32):
            v = img[y][x]
            if v == 0:
                continue
            is_boundary = False
            for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
                nx, ny = x+dx, y+dy
                if not in_bounds(nx, ny) or img[ny][nx] == 0:
                    is_boundary = True
                    break
            if is_boundary:
                bset.add((x,y))

    vals = []
    for y in range(32):
        for x in range(32):
            if (x,y) in bset:
                continue
            v = img[y][x]
            if v != 0:
                vals.append(v)
    return vals


@dataclass
class FrameRoles:
    outline: int
    fill: int
    accent: Optional[int]


def detect_roles(img: List[List[int]], boundary_min: int, boundary_gap: float) -> Tuple[Optional[FrameRoles], str]:
    bvals = boundary_pixels(img)

    # Exclude cream (4) from being considered "outline" because you want it preserved and it's not the outline in Spaceworld.
    bvals2 = [v for v in bvals if v not in (0, 4)]
    if len(bvals2) < boundary_min:
        return None, f"boundary_nonzero<{boundary_min} (got {len(bvals2)})"

    bc = Counter(bvals2)
    top = bc.most_common(3)
    if not top:
        return None, "no_boundary_indices"

    outline = top[0][0]
    if len(top) >= 2 and top[0][1] < boundary_gap * top[1][1]:
        return None, f"boundary_ambiguous top={top[:2]} need_gap={boundary_gap:.2f}"

    # Determine fill/accent from interior (prefer actual interior; fallback to all nonzero if needed)
    ivals = interior_pixels(img)
    if not ivals:
        # fallback: all nonzero pixels excluding 0
        ivals = [img[y][x] for y in range(32) for x in range(32) if img[y][x] != 0]

    # exclude 0, outline, and 4 (cream preserved)
    ivals2 = [v for v in ivals if v not in (0, 4, outline)]
    if not ivals2:
        return None, "no_interior_candidates"

    ic = Counter(ivals2)
    fill = ic.most_common(1)[0][0]

    accent = None
    for idx, _count in ic.most_common():
        if idx != fill:
            accent = idx
            break

    return FrameRoles(outline=outline, fill=fill, accent=accent), "ok"


def remap_image(img: List[List[int]], roles: FrameRoles) -> Tuple[List[List[int]], dict, bool]:
    """
    Remap old indices -> new desired:
      outline -> 2
      fill    -> 1
      accent  -> 3 (optional)
    Preserve 0 and 4 always.
    """
    desired = {roles.outline: 2, roles.fill: 1}
    if roles.accent is not None and roles.accent not in (roles.outline, roles.fill):
        desired[roles.accent] = 3

    # refuse if any role hits forbidden indices
    for old in desired.keys():
        if old in (0, 4):
            return img, {}, False

    # if already correct, no change
    if all(old == new for old, new in desired.items()):
        return img, desired, False

    lut = list(range(16))
    for old, new in desired.items():
        lut[old] = new
    lut[0] = 0
    lut[4] = 4

    new_img = [[lut[p] for p in row] for row in img]
    changed = any(new_img[y][x] != img[y][x] for y in range(32) for x in range(32))
    return new_img, desired, changed


def process_file(path: Path, boundary_min: int, boundary_gap: float, apply: bool, backup_dir: Path):
    data = path.read_bytes()
    frames_bytes = split_frames(data)
    if not frames_bytes:
        return ("SKIP", f"unsupported_size {len(data)}", False)

    new_frames = []
    any_changed = False
    roles_summary = []

    for i, fb in enumerate(frames_bytes):
        img = decode_4bpp_32x32(fb)
        roles, reason = detect_roles(img, boundary_min=boundary_min, boundary_gap=boundary_gap)
        if roles is None:
            return ("SKIP", f"frame{i}:{reason}", False)

        new_img, mapping, changed = remap_image(img, roles)
        roles_summary.append(f"frame{i}: outline={roles.outline} fill={roles.fill} accent={roles.accent}")
        new_frames.append(encode_4bpp_32x32(new_img))
        any_changed = any_changed or changed

    if apply and any_changed:
        backup_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, backup_dir / path.name)
        path.write_bytes(b"".join(new_frames))

    return ("FIX" if any_changed else "OK", "; ".join(roles_summary), any_changed)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--icons", required=True)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--boundary-min", type=int, default=80, help="Min boundary pixels excluding 0 and 4")
    ap.add_argument("--boundary-gap", type=float, default=1.20, help="Outline winner >= gap * runner-up on boundary")
    args = ap.parse_args()

    if args.apply and args.dry_run:
        raise SystemExit("Choose only one: --apply or --dry-run")

    icons_dir = Path(args.icons)
    if not icons_dir.is_dir():
        raise SystemExit(f"Not a directory: {icons_dir}")

    files = sorted(icons_dir.glob("*.4bpp"))
    if not files:
        raise SystemExit(f"No .4bpp found in {icons_dir}")

    apply = args.apply and not args.dry_run
    stamp = time.strftime("%Y%m%d_%H%M%S")
    backup_dir = icons_dir.parent / f"_icon_backups_{stamp}"

    print(f"Scanning {len(files)} icons in {icons_dir}")
    print(f"Mode: {'APPLY' if apply else 'DRY-RUN'}")
    if apply:
        print(f"Backups will be written to: {backup_dir}")

    fixed = ok = skipped = 0
    for f in files:
        status, info, changed = process_file(f, args.boundary_min, args.boundary_gap, apply, backup_dir)
        if status == "SKIP":
            skipped += 1
            print(f"[SKIP] {f.name}: {info}")
        elif status == "OK":
            ok += 1
            print(f"[OK  ] {f.name}: {info}")
        else:
            fixed += 1
            print(f"[FIX ] {f.name}: {info}")

    print("\nSummary")
    print(f"  fixed:   {fixed}")
    print(f"  ok:      {ok}")
    print(f"  skipped: {skipped}")
    if apply:
        print(f"Backups: {backup_dir}")

if __name__ == "__main__":
    main()
