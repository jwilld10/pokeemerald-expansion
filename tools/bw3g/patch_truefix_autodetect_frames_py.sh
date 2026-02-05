#!/usr/bin/env bash
set -euo pipefail

FILE="tools/bw3g/png_to_smol_spaceworld.py"
[[ -f "$FILE" ]] || { echo "ERROR: missing $FILE"; exit 1; }

cp -v "$FILE" "$FILE.bak_autoframes_$(date +%Y%m%d_%H%M%S)"

python3 - <<'PY'
from pathlib import Path

path = Path("tools/bw3g/png_to_smol_spaceworld.py")
text = path.read_text(encoding="utf-8").splitlines(True)

# Find the split_strip function start
start = None
for i, line in enumerate(text):
    if line.startswith("def split_strip("):
        start = i
        break
if start is None:
    raise SystemExit("ERROR: could not find 'def split_strip(' in png_to_smol_spaceworld.py")

# Find end of the function: next top-level def (column 0) after start
end = None
for j in range(start + 1, len(text)):
    if text[j].startswith("def ") and not text[j].startswith("def split_strip("):
        end = j
        break
if end is None:
    end = len(text)

new_func = """def split_strip(img_rgba, frame_w, frame_h):
    \"\"\"Return a list of frame images.

    IMPORTANT: BW3G source PNG pixel dims often do NOT equal SpeciesInfo MON_COORDS_SIZE.
    The coords size is a display/crop hint; the PNG is the real art canvas.

    Strategy:
      1) Try the provided frame_w/frame_h strip rules if they match.
      2) If not, auto-detect:
         - if PNG fits in 64x64 => single frame
         - else if it looks like a vertical/horizontal strip of equal-sized square frames (<=64) => split
    \"\"\"
    w, h = img_rgba.size
    frames = []

    # --- 1) Try explicit frame size if it matches strip rules ---
    if frame_w and frame_h:
        if w == frame_w and h == frame_h:
            return [img_rgba]
        if w == frame_w and h % frame_h == 0:
            n = h // frame_h
            for i in range(n):
                frames.append(img_rgba.crop((0, i*frame_h, frame_w, (i+1)*frame_h)))
            return frames
        if h == frame_h and w % frame_w == 0:
            n = w // frame_w
            for i in range(n):
                frames.append(img_rgba.crop((i*frame_w, 0, (i+1)*frame_w, frame_h)))
            return frames

    # --- 2) Auto-detect based on the PNG itself ---
    # If it fits in 64x64, treat it as a single frame. (Common: 56x56, etc.)
    if w <= 64 and h <= 64:
        return [img_rgba]

    # Vertical strip of square frames (common ripping format)
    if w <= 64 and h % w == 0:
        n = h // w
        if n >= 2:
            for i in range(n):
                frames.append(img_rgba.crop((0, i*w, w, (i+1)*w)))
            return frames

    # Horizontal strip of square frames
    if h <= 64 and w % h == 0:
        n = w // h
        if n >= 2:
            for i in range(n):
                frames.append(img_rgba.crop((i*h, 0, (i+1)*h, h)))
            return frames

    raise ValueError(f"PNG size {w}x{h} could not be split (frame hint {frame_w}x{frame_h}).")

""".splitlines(True)

patched = text[:start] + new_func + text[end:]
path.write_text("".join(patched), encoding="utf-8")
print(f"OK: replaced split_strip() block in {path}")
PY
