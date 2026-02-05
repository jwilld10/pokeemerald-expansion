#!/usr/bin/env bash
set -euo pipefail

FILE="tools/bw3g/png_to_smol_spaceworld.py"
[[ -f "$FILE" ]] || { echo "ERROR: missing $FILE"; exit 1; }

cp -v "$FILE" "$FILE.bak_autoframes_$(date +%Y%m%d_%H%M%S)"

perl -0777 -i -pe '
s/def split_strip\(img_rgba, frame_w, frame_h\):.*?\n\s*raise ValueError\(f"PNG size \{w\}x\{h\} doesn\x27t match strip rules for frame \{frame_w\}x\{frame_h\}"\)\n\n/def split_strip(img_rgba, frame_w, frame_h):\n    \"\"\"Return a list of frame images.\n\n    IMPORTANT: BW3G source PNG pixel dims often do NOT equal SpeciesInfo MON_COORDS_SIZE.\n    The coords size is a display/crop hint; the PNG is the real art canvas.\n\n    Strategy:\n      1) Try the provided frame_w/frame_h strip rules if they match.\n      2) If not, auto-detect:\n         - if PNG fits in 64x64 => single frame\n         - else if it looks like a vertical/horizontal strip of equal-sized frames (<=64) => split\n    \"\"\"\n    w, h = img_rgba.size\n    frames = []\n\n    # --- 1) Try explicit frame size if it matches strip rules ---\n    if frame_w and frame_h:\n        if w == frame_w and h == frame_h:\n            return [img_rgba]\n        if w == frame_w and h % frame_h == 0:\n            n = h // frame_h\n            for i in range(n):\n                frames.append(img_rgba.crop((0, i*frame_h, frame_w, (i+1)*frame_h)))\n            return frames\n        if h == frame_h and w % frame_w == 0:\n            n = w // frame_w\n            for i in range(n):\n                frames.append(img_rgba.crop((i*frame_w, 0, (i+1)*frame_w, frame_h)))\n            return frames\n\n    # --- 2) Auto-detect based on the PNG itself ---\n    # If it fits in 64x64, treat it as a single frame. (Most BW3G fronts are like this: 56x56, etc.)\n    if w <= 64 and h <= 64:\n        return [img_rgba]\n\n    # Vertical strip of square frames (common ripping format)\n    if w <= 64 and h % w == 0:\n        n = h // w\n        if n >= 2 and w <= 64:\n            for i in range(n):\n                frames.append(img_rgba.crop((0, i*w, w, (i+1)*w)))\n            return frames\n\n    # Horizontal strip of square frames\n    if h <= 64 and w % h == 0:\n        n = w // h\n        if n >= 2 and h <= 64:\n            for i in range(n):\n                frames.append(img_rgba.crop((i*h, 0, (i+1)*h, h)))\n            return frames\n\n    raise ValueError(f\"PNG size {w}x{h} could not be split (frame hint {frame_w}x{frame_h}).\")\n\n/sms
' "$FILE"

echo "OK: patched split_strip() to auto-detect frames when SpeciesInfo sizes don't match PNG."
