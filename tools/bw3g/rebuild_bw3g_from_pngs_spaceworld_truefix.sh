#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUTROOT="$ROOT/graphics/bw3g/pokemon"

# Where your BW3G PNGs actually live (from your diag)
BW3G_PNG_ROOT="/home/jwilld10/decomps/gb/BW3G/gfx/pokemon"

FAMILIES="$ROOT/src/data/pokemon/species_info/bw3g_families.h"

echo "== Repo root =="
echo "$ROOT"
echo
echo "== BW3G PNG ROOT =="
echo "$BW3G_PNG_ROOT"
echo

if [[ ! -d "$BW3G_PNG_ROOT" ]]; then
  echo "ERROR: BW3G_PNG_ROOT not found: $BW3G_PNG_ROOT"
  exit 1
fi

if [[ ! -f "$FAMILIES" ]]; then
  echo "ERROR: bw3g_families.h not found: $FAMILIES"
  exit 1
fi

# 1) Ensure compresSmol exists (build it if needed)
SMOL_TOOL="$ROOT/tools/compresSmol/compresSmol"
if [[ ! -x "$SMOL_TOOL" ]]; then
  echo "== Building compresSmol =="
  pushd "$ROOT/tools/compresSmol" >/dev/null
  # Build both binaries if needed
  g++ -O2 -std=c++17 -o compresSmol compresSmol.cpp
  g++ -O2 -std=c++17 -o compresSmolTilemap compresSmolTilemap.cpp
  popd >/dev/null
fi

if [[ ! -x "$SMOL_TOOL" ]]; then
  echo "ERROR: compresSmol did not build: $SMOL_TOOL"
  exit 1
fi

# 2) Write python converter (Spaceworld rules: tiled, 2-frame anim_front, palette[0]=transparent)
PY="$ROOT/tools/bw3g/png_to_smol_spaceworld.py"
cat > "$PY" <<'PY'
#!/usr/bin/env python3
import os, re, sys, struct, subprocess
from PIL import Image

# --- GBA helpers ---
def rgb888_to_bgr555(r, g, b):
    # 0..255 -> 0..31, GBA is BGR555
    r5 = (r * 31 + 127) // 255
    g5 = (g * 31 + 127) // 255
    b5 = (b * 31 + 127) // 255
    return (b5 << 10) | (g5 << 5) | r5

def write_gbapal(path, palette_rgb16):
    # palette_rgb16: list of (r,g,b) length 16
    data = bytearray()
    for (r,g,b) in palette_rgb16:
        data += struct.pack("<H", rgb888_to_bgr555(r,g,b))
    with open(path, "wb") as f:
        f.write(data)

def pad_to_64(img_rgba):
    w, h = img_rgba.size
    # center it on 64x64
    canvas = Image.new("RGBA", (64,64), (0,0,0,0))
    ox = (64 - w) // 2
    oy = (64 - h) // 2
    canvas.paste(img_rgba, (ox, oy))
    return canvas

def split_strip(img_rgba, frame_w, frame_h):
    w, h = img_rgba.size
    frames = []
    # If already exact frame size, single frame
    if w == frame_w and h == frame_h:
        frames.append(img_rgba)
        return frames
    # Vertical strip: w == frame_w and h multiple of frame_h
    if w == frame_w and h % frame_h == 0:
        n = h // frame_h
        for i in range(n):
            frames.append(img_rgba.crop((0, i*frame_h, frame_w, (i+1)*frame_h)))
        return frames
    # Horizontal strip: h == frame_h and w multiple of frame_w
    if h == frame_h and w % frame_w == 0:
        n = w // frame_w
        for i in range(n):
            frames.append(img_rgba.crop((i*frame_w, 0, (i+1)*frame_w, frame_h)))
        return frames

    raise ValueError(f"PNG size {w}x{h} doesn't match strip rules for frame {frame_w}x{frame_h}")

def quantize_15_plus_transparency(img_rgba_64):
    # We want 16 entries total:
    #   index 0 = transparency color (unused except transparent pixels)
    #   indices 1..15 = 15-color palette for opaque pixels
    rgba = img_rgba_64
    w, h = rgba.size
    assert (w,h) == (64,64)

    px = rgba.getdata()
    opaque = Image.new("RGB", (64,64), (0,0,0))
    opaque_px = []
    alpha_mask = []
    for (r,g,b,a) in px:
        alpha_mask.append(a)
        # for palette learning, only opaque contributes; transparent becomes black but masked out later
        opaque_px.append((r,g,b))
    opaque.putdata(opaque_px)

    # Quantize to 15 colors on RGB (no alpha errors)
    q = opaque.quantize(colors=15, method=Image.FASTOCTREE)
    pal = q.getpalette()  # 256*3 list
    # First 15 colors from q palette
    pal15 = [(pal[i*3], pal[i*3+1], pal[i*3+2]) for i in range(15)]

    # Build final 16-color palette: [transparent] + pal15
    final_pal = [(0,0,0)] + pal15

    # Build indexed image (mode 'P') with our palette, mapping:
    #   transparent pixels -> 0
    #   opaque pixels -> q_index + 1
    q_idx = list(q.getdata())
    out_idx = []
    for i in range(64*64):
        if alpha_mask[i] == 0:
            out_idx.append(0)
        else:
            out_idx.append(q_idx[i] + 1)
    return final_pal, out_idx

def idx_to_4bpp_tiled_bytes(idx, width=64, height=64):
    # idx: list length width*height, values 0..15
    # Convert to GBA 4bpp tiled order (8x8 tiles, row-major), 2 pixels per byte (low nibble first)
    out = bytearray()
    tiles_x = width // 8
    tiles_y = height // 8
    for ty in range(tiles_y):
        for tx in range(tiles_x):
            # each tile: 8 rows, each row 8 pixels => 4 bytes
            for row in range(8):
                base = (ty*8 + row) * width + (tx*8)
                for colpair in range(4):
                    p0 = idx[base + colpair*2] & 0xF
                    p1 = idx[base + colpair*2 + 1] & 0xF
                    out.append(p0 | (p1 << 4))
    return bytes(out)

def make_anim_front(front_png, frame_w, frame_h):
    img = Image.open(front_png).convert("RGBA")
    frames = split_strip(img, frame_w, frame_h)

    # Need exactly 2 frames for Emerald-style anim_front
    if len(frames) == 1:
        f0 = frames[0]
        f1 = frames[0]
    else:
        f0 = frames[0]
        f1 = frames[1]

    f0 = pad_to_64(f0)
    f1 = pad_to_64(f1)

    # Build palette from frame0 only (Spaceworld-style: one palette per mon)
    pal16, idx0 = quantize_15_plus_transparency(f0)

    # Apply SAME palette mapping to frame1:
    # simplest: quantize frame1 to same palette by nearest match
    # We'll do brute nearest among pal16[1..15], reserving 0 for transparent.
    def map_to_pal(img_rgba):
        px = list(img_rgba.getdata())
        out = []
        for (r,g,b,a) in px:
            if a == 0:
                out.append(0)
                continue
            best = 1
            bestd = 10**18
            for j in range(1,16):
                pr,pg,pb = pal16[j]
                d = (r-pr)*(r-pr) + (g-pg)*(g-pg) + (b-pb)*(b-pb)
                if d < bestd:
                    bestd = d
                    best = j
            out.append(best)
        return out

    idx1 = map_to_pal(f1)

    raw0 = idx_to_4bpp_tiled_bytes(idx0)
    raw1 = idx_to_4bpp_tiled_bytes(idx1)
    assert len(raw0) == 2048 and len(raw1) == 2048
    return pal16, raw0 + raw1  # 4096 bytes

def make_back(back_png, frame_w, frame_h, pal16):
    img = Image.open(back_png).convert("RGBA")
    frames = split_strip(img, frame_w, frame_h)
    f = frames[0]
    f = pad_to_64(f)

    # map to existing pal16
    px = list(f.getdata())
    out = []
    for (r,g,b,a) in px:
        if a == 0:
            out.append(0)
            continue
        best = 1
        bestd = 10**18
        for j in range(1,16):
            pr,pg,pb = pal16[j]
            d = (r-pr)*(r-pr) + (g-pg)*(g-pg) + (b-pb)*(b-pb)
            if d < bestd:
                bestd = d
                best = j
        out.append(best)
    raw = idx_to_4bpp_tiled_bytes(out)
    assert len(raw) == 2048
    return raw

def run_compresSmol(compresSmol, in4bpp, outsmol):
    # -w compress
    subprocess.check_call([compresSmol, "-w", in4bpp, outsmol])

def main():
    if len(sys.argv) != 9:
        print("usage: png_to_smol_spaceworld.py <compresSmol> <front_png> <back_png> <out_anim_front_smol> <out_back_smol> <out_pal> <frame_w> <frame_h>")
        sys.exit(2)

    compresSmol, front_png, back_png, out_front_smol, out_back_smol, out_pal, fw, fh = sys.argv[1:]
    fw = int(fw); fh = int(fh)

    pal16, anim_front_raw = make_anim_front(front_png, fw, fh)

    # write palette
    write_gbapal(out_pal, pal16)

    # write raw temps
    tmp_front = out_front_smol + ".tmp.4bpp"
    tmp_back  = out_back_smol  + ".tmp.4bpp"
    with open(tmp_front, "wb") as f:
        f.write(anim_front_raw)

    back_raw = make_back(back_png, fw, fh, pal16)
    with open(tmp_back, "wb") as f:
        f.write(back_raw)

    # compress to smol
    run_compresSmol(compresSmol, tmp_front, out_front_smol)
    run_compresSmol(compresSmol, tmp_back, out_back_smol)

    os.remove(tmp_front)
    os.remove(tmp_back)

if __name__ == "__main__":
    main()
PY
chmod +x "$PY"

# 3) Parse size map from bw3g_families.h (MON_COORDS_SIZE(w,h))
# We key by folder name (lowercase) because your folder names look like that.
TMPMAP="/tmp/bw3g_sizes.map"
python3 - <<PY > "$TMPMAP"
import re, sys
text = open("$FAMILIES","r",encoding="utf-8",errors="ignore").read()
# Find blocks and pick the first ".frontPicSize = MON_COORDS_SIZE(w, h)" inside each species block,
# then grab the mon folder name from the gMonFrontPic_<NAME>Bw3g symbol.
# We'll map folder name = lower(name)
pat = re.compile(r"\.frontPic\s*=\s*\(const u32\s*\*\)\s*gMonFrontPic_([A-Z0-9_]+)Bw3g.*?\.frontPicSize\s*=\s*MON_COORDS_SIZE\(\s*(\d+)\s*,\s*(\d+)\s*\)", re.S)
seen = {}
for m in pat.finditer(text):
    name = m.group(1)
    w = int(m.group(2)); h = int(m.group(3))
    folder = name.lower()
    if folder not in seen:
        seen[folder] = (w,h)
for k,(w,h) in sorted(seen.items()):
    print(f"{k} {w} {h}")
PY

LINES=$(wc -l < "$TMPMAP" | tr -d ' ')
echo "== Size map =="
echo "wrote: $TMPMAP (lines=$LINES)"
echo

# 4) Convert each mon that has sizes + pngs
converted=0
skipped=0
missing_size=0
missing_png=0
too_big=0

while read -r mon w h; do
  srcdir="$BW3G_PNG_ROOT/$mon"
  front_png="$srcdir/front.png"
  back_png="$srcdir/back.png"

  if [[ ! -f "$front_png" || ! -f "$back_png" ]]; then
    missing_png=$((missing_png+1))
    skipped=$((skipped+1))
    continue
  fi

  # If frame bigger than 64, we can't fit without scaling (which you probably don't want).
  if (( w > 64 || h > 64 )); then
    too_big=$((too_big+1))
    skipped=$((skipped+1))
    continue
  fi

  outdir="$OUTROOT/$mon"
  mkdir -p "$outdir"
  python3 "$PY" "$SMOL_TOOL" "$front_png" "$back_png" \
    "$outdir/anim_front.4bpp.smol" "$outdir/back.4bpp.smol" "$outdir/normal.gbapal" \
    "$w" "$h"

  converted=$((converted+1))
done < "$TMPMAP"

echo "== Done =="
echo "converted=$converted skipped=$skipped (missing_png=$missing_png too_big=$too_big)"
echo
echo "Next: rebuild with: make -j"
