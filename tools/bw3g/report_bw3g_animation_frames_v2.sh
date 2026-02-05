#!/usr/bin/env bash
set -euo pipefail

BW3G_PNG_ROOT="${BW3G_PNG_ROOT:-/home/jwilld10/decomps/gb/BW3G/gfx/pokemon}"
OUT="bw3g_animation_frames_report_v2.out.txt"

python3 - <<'PY' "$BW3G_PNG_ROOT" "$OUT"
import sys
from pathlib import Path

png_root = Path(sys.argv[1])
out_path = Path(sys.argv[2])

try:
    from PIL import Image
except Exception:
    raise SystemExit("ERROR: Pillow missing. Install: sudo apt-get install python3-pil")

CAND = [40, 48, 56, 64]

def infer(w, h):
    """
    Infer frames + layout from PNG dimensions.
    Priority:
      1) exact single-frame square
      2) vstrip of square frames (w in CAND, h multiple of w)
      3) hstrip of square frames (h in CAND, w multiple of h)
      4) vstrip with candidate frame_w (w in CAND, h multiple of frame_h from CAND)
      5) grid/sheet with candidate frame sizes
      6) unknown
    Returns: (frames, layout, fw, fh, grid_w, grid_h)
    """

    # 1) exact square single frame (any square)
    if w == h:
        return (1, "exact_square", w, h, 1, 1)

    # 2) vertical strip of square frames (frame = w)
    if h % w == 0:
        n = h // w
        # if w is a common candidate, label as likely
        layout = "vstrip_square"
        return (n, layout, w, w, 1, n)

    # 3) horizontal strip of square frames (frame = h)
    if w % h == 0:
        n = w // h
        return (n, "hstrip_square", h, h, n, 1)

    # 4) candidate-based vstrip/hstrip (non-square frames)
    for fw in CAND:
        for fh in CAND:
            if w == fw and h % fh == 0:
                return (h // fh, "vstrip_cand", fw, fh, 1, h // fh)
            if h == fh and w % fw == 0:
                return (w // fw, "hstrip_cand", fw, fh, w // fw, 1)

    # 5) sheet/grid with candidate frame sizes
    best = None
    for fw in CAND:
        for fh in CAND:
            if w % fw == 0 and h % fh == 0:
                gw = w // fw
                gh = h // fh
                frames = gw * gh
                # prefer “skinny” sheets less; prefer small gw*gh maybe
                score = (frames, abs(gw-gh), fw*fh)
                if best is None or score < best[0]:
                    best = (score, frames, fw, fh, gw, gh)
    if best:
        _, frames, fw, fh, gw, gh = best
        return (frames, "sheet_cand", fw, fh, gw, gh)

    return (None, "unknown", None, None, None, None)

lines = []
lines.append("== BW3G animation frame report (v2: infer from PNG dims) ==")
lines.append(f"PNG root: {png_root}")
lines.append("")
lines.append("Format:")
lines.append("mon | front WxH => frames layout frame=fw x fh (grid gw x gh) | back WxH => ...")
lines.append("")

tot = 0
unknown = 0
multi_front = 0
multi_back = 0
by_front_frame = {}
by_front_frames = {}

for mon_dir in sorted([p for p in png_root.iterdir() if p.is_dir()]):
    fp = mon_dir / "front.png"
    bp = mon_dir / "back.png"
    if not fp.exists() or not bp.exists():
        continue

    with Image.open(fp) as im:
        fW, fH = im.size
    with Image.open(bp) as im:
        bW, bH = im.size

    f_frames, f_layout, fw, fh, fgw, fgh = infer(fW, fH)
    b_frames, b_layout, bw, bh, bgw, bgh = infer(bW, bH)

    tot += 1
    if f_frames is None:
        unknown += 1
    if f_frames and f_frames > 1:
        multi_front += 1
    if b_frames and b_frames > 1:
        multi_back += 1

    if fw and fh:
        by_front_frame[(fw, fh)] = by_front_frame.get((fw, fh), 0) + 1
    if f_frames:
        by_front_frames[f_frames] = by_front_frames.get(f_frames, 0) + 1

    def fmt(frames, layout, fw, fh, gw, gh):
        if frames is None:
            return "? (unknown)"
        if layout.startswith("sheet"):
            return f"{frames} ({layout} frame={fw}x{fh} grid={gw}x{gh})"
        if layout.startswith("vstrip") or layout.startswith("hstrip"):
            return f"{frames} ({layout} frame={fw}x{fh})"
        return f"{frames} ({layout} frame={fw}x{fh})"

    lines.append(
        f"{mon_dir.name} | "
        f"front {fW}x{fH} => {fmt(f_frames, f_layout, fw, fh, fgw, fgh)} | "
        f"back {bW}x{bH} => {fmt(b_frames, b_layout, bw, bh, bgw, bgh)}"
    )

# Append summary tables
lines.append("")
lines.append("== Summary ==")
lines.append(f"mons_scanned = {tot}")
lines.append(f"front_unknown = {unknown}")
lines.append(f"front_multi_frame = {multi_front}")
lines.append(f"back_multi_frame = {multi_back}")
lines.append("")
lines.append("Front inferred frame sizes (count):")
for (fw, fh), c in sorted(by_front_frame.items(), key=lambda x: (-x[1], x[0][0], x[0][1])):
    lines.append(f"  {fw}x{fh}: {c}")
lines.append("")
lines.append("Front inferred frame counts (count):")
for k, v in sorted(by_front_frames.items(), key=lambda x: (x[0], -x[1])):
    lines.append(f"  {k}: {v}")

out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"WROTE: {out_path}")
print("")
print("Tail summary (last ~25 lines):")
print("\n".join(lines[-25:]))
PY
