#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
BW3G_PNG_ROOT="${BW3G_PNG_ROOT:-/home/jwilld10/decomps/gb/BW3G/gfx/pokemon}"
OUTROOT="$ROOT/graphics/bw3g/pokemon"
SMOL_BIN="$ROOT/tools/compresSmol/compresSmol"

if [[ ! -x "$SMOL_BIN" ]]; then
  echo "ERROR: missing smol tool: $SMOL_BIN"
  echo "Try building it: (cd tools/compresSmol && make)  # if it has a Makefile"
  exit 1
fi

python3 - <<'PY' "$BW3G_PNG_ROOT" "$OUTROOT" "$SMOL_BIN"
import sys, subprocess
from pathlib import Path
from PIL import Image

png_root = Path(sys.argv[1])
out_root = Path(sys.argv[2])
smol_bin = Path(sys.argv[3])

def split_strip_autodetect(img_rgba):
    """
    BW3G rule (based on your report):
      - Most animated fronts are vertical strips of square frames.
      - Frame size = PNG width (40/48/56 typical).
      - frames = height / width if divisible.
      - If height == width -> 1 frame.
      - If width % height == 0 -> horizontal strip of square frames (rare, but handle).
    """
    w, h = img_rgba.size

    # exact single frame
    if w == h:
        return [img_rgba], w, h

    # vertical strip of square frames
    if h % w == 0:
        fh = w
        n = h // fh
        frames = [img_rgba.crop((0, i*fh, w, (i+1)*fh)) for i in range(n)]
        return frames, w, fh

    # horizontal strip of square frames
    if w % h == 0:
        fw = h
        n = w // fw
        frames = [img_rgba.crop((i*fw, 0, (i+1)*fw, h)) for i in range(n)]
        return frames, fw, h

    raise ValueError(f"unknown strip layout {w}x{h} (not square, not clean vstrip/hstrip)")

def reserve_index0_quantize(frames_rgba):
    """
    Build a 16-color palette where index 0 is reserved for transparency.
    White must NOT land on index 0 (this fixes your 'white is transparent' issue).
    """
    fw, fh = frames_rgba[0].size

    # build a big RGB image for palette extraction (transparent -> magenta)
    big = Image.new("RGBA", (fw, fh*len(frames_rgba)), (0,0,0,0))
    for i, fr in enumerate(frames_rgba):
        big.paste(fr, (0, i*fh))

    big2 = big.copy()
    px = big2.load()
    for y in range(big2.size[1]):
        for x in range(big2.size[0]):
            r,g,b,a = px[x,y]
            if a == 0:
                px[x,y] = (255,0,255,255)

    # quantize visible colors to 15
    q = big2.convert("RGB").quantize(colors=15, method=2)  # FASTOCTREE
    pal = q.getpalette()[:15*3]
    vis = [(pal[i], pal[i+1], pal[i+2]) for i in range(0, len(pal), 3)]
    full = [(0,0,0)] + vis  # index0 reserved

    pal_flat = []
    for (r,g,b) in full:
        pal_flat += [r,g,b]
    pal_flat += [0,0,0] * (256-16)

    def nearest(rgb):
        r,g,b = rgb
        best_i = 1
        best_d = 10**18
        for i in range(1,16):
            pr,pg,pb = full[i]
            d = (r-pr)*(r-pr)+(g-pg)*(g-pg)+(b-pb)*(b-pb)
            if d < best_d:
                best_d = d
                best_i = i
        return best_i

    indexed = []
    for fr in frames_rgba:
        fr = fr.convert("RGBA")
        out = Image.new("P", fr.size, 0)
        out.putpalette(pal_flat)
        src = fr.load()
        dst = out.load()
        for y in range(fr.size[1]):
            for x in range(fr.size[0]):
                r,g,b,a = src[x,y]
                if a == 0:
                    dst[x,y] = 0
                else:
                    dst[x,y] = nearest((r,g,b))
        indexed.append(out)

    # gbapal: 16 colors -> BGR555 little endian
    def rgb_to_bgr555(c):
        r,g,b = c
        r5 = (r * 31 + 127)//255
        g5 = (g * 31 + 127)//255
        b5 = (b * 31 + 127)//255
        val = (b5<<10) | (g5<<5) | (r5)
        return val.to_bytes(2, "little")

    gbapal = b"".join(rgb_to_bgr555(c) for c in full)
    return indexed, gbapal

def to_4bpp_tiled(imgP, canvas_w=64, canvas_h=64):
    """
    Put the frame onto a 64x64 canvas (bottom-aligned, centered),
    then emit GBA 4bpp tiled (8x8) bytes.
    """
    fw, fh = imgP.size
    canvas = Image.new("P", (canvas_w, canvas_h), 0)
    canvas.putpalette(imgP.getpalette())

    ox = (canvas_w - fw)//2
    oy = canvas_h - fh
    canvas.paste(imgP, (ox, oy))

    pix = canvas.load()
    out = bytearray()
    for ty in range(0, canvas_h, 8):
        for tx in range(0, canvas_w, 8):
            for y in range(8):
                for x in range(0,8,2):
                    a = pix[tx+x, ty+y] & 0xF
                    b = pix[tx+x+1, ty+y] & 0xF
                    out.append(a | (b<<4))
    return bytes(out)

mons = sorted([p for p in png_root.iterdir() if p.is_dir()])
converted = 0
skipped = 0
reasons = {"no_front":0, "unknown_layout":0, "smol_fail":0}

for mon_dir in mons:
    mon = mon_dir.name
    front_png = mon_dir / "front.png"
    if not front_png.exists():
        skipped += 1; reasons["no_front"] += 1
        continue

    try:
        img = Image.open(front_png).convert("RGBA")
        frames_rgba, fw, fh = split_strip_autodetect(img)

        indexed_frames, gbapal = reserve_index0_quantize(frames_rgba)

        out_dir = out_root / mon
        out_dir.mkdir(parents=True, exist_ok=True)

        (out_dir / "normal.gbapal").write_bytes(gbapal)

        raw = b"".join(to_4bpp_tiled(fr) for fr in indexed_frames)
        tmp_raw = out_dir / "anim_front.4bpp"
        tmp_raw.write_bytes(raw)

        out_smol = out_dir / "anim_front.4bpp.smol"
        try:
            subprocess.check_call([str(smol_bin), "-w", str(tmp_raw), str(out_smol)])
        except Exception:
            skipped += 1; reasons["smol_fail"] += 1
            continue

        converted += 1

    except Exception:
        skipped += 1; reasons["unknown_layout"] += 1
        continue

print("== BW3G anim_front smol rebuild (autodetect frames) ==")
print(f"PNG root: {png_root}")
print(f"Converted: {converted}")
print(f"Skipped:   {skipped}  reasons={reasons}")
print("")
print("Wrote:")
print("  graphics/bw3g/pokemon/<mon>/anim_front.4bpp.smol")
print("  graphics/bw3g/pokemon/<mon>/normal.gbapal  (index0 reserved transparent)")
PY
