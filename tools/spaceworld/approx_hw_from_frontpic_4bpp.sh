#!/usr/bin/env bash
set -euo pipefail

OUT_H="src/data/pokemon/spaceworld_generated/spaceworld_species_info.h"

python3 - "$OUT_H" <<'PY'
import re, sys, math, subprocess
from pathlib import Path

OUT_H = Path(sys.argv[1])
txt = OUT_H.read_text(encoding="utf-8", errors="ignore")

# ------------------ small utilities ------------------

def linfit(xs, ys):
    n = len(xs)
    if n < 2:
        return (1.0, 0.0)
    sx = sum(xs); sy = sum(ys)
    sxx = sum(x*x for x in xs)
    sxy = sum(x*y for x,y in zip(xs,ys))
    denom = n*sxx - sx*sx
    if abs(denom) < 1e-9:
        return (1.0, 0.0)
    a = (n*sxy - sx*sy) / denom
    b = (sy - a*sx) / n
    return (a, b)

def clamp_int(v, lo, hi):
    return int(max(lo, min(hi, v)))

def run_rg(pattern, path="."):
    # return first few matching lines quickly
    p = subprocess.run(
        ["rg", "-n", "-S", "--no-heading", "--max-count", "20", pattern, path],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    return p.stdout.splitlines()

# GBA LZ77 decompression (type 0x10)
def gba_lz77_decompress(data: bytes) -> bytes:
    if len(data) < 4 or data[0] != 0x10:
        return data
    out_len = data[1] | (data[2] << 8) | (data[3] << 16)
    src = 4
    out = bytearray()
    while len(out) < out_len and src < len(data):
        flags = data[src]
        src += 1
        for bit in range(7, -1, -1):
            if len(out) >= out_len or src >= len(data):
                break
            if (flags >> bit) & 1 == 0:
                out.append(data[src])
                src += 1
            else:
                if src + 1 >= len(data):
                    break
                b1 = data[src]; b2 = data[src+1]
                src += 2
                length = (b1 >> 4) + 3
                disp = ((b1 & 0x0F) << 8) | b2
                disp += 1
                for _ in range(length):
                    if len(out) >= out_len:
                        break
                    out.append(out[-disp])
    return bytes(out)

def frontpic_metrics_from_4bpp(raw: bytes, size_px=64):
    # Interpret as 4bpp tiled data, assume 64x64 (8x8 tiles).
    # tile: 8x8 pixels, 32 bytes. 64x64 => 8*8 = 64 tiles => 2048 bytes.
    need = (size_px * size_px) // 2  # 2 pixels per byte in 4bpp
    if len(raw) < need:
        return None
    raw = raw[:need]

    # Expand to pixel indices for a tiled image:
    tiles_per_row = size_px // 8
    # build pixel array on the fly and compute bbox/area where pix != 0
    minx, miny = size_px, size_px
    maxx, maxy = -1, -1
    area = 0

    # helper to read pixel in tile order
    # tile index = (ty * tiles_per_row + tx)
    # within tile: row 0..7, col 0..7; byte holds (col_even pix_low, col_odd pix_high)
    for ty in range(tiles_per_row):
        for tx in range(tiles_per_row):
            tile_index = ty * tiles_per_row + tx
            tile_off = tile_index * 32
            for row in range(8):
                row_off = tile_off + row * 4
                for col_pair in range(4):
                    b = raw[row_off + col_pair]
                    p0 = b & 0x0F
                    p1 = (b >> 4) & 0x0F
                    x0 = tx * 8 + col_pair * 2
                    x1 = x0 + 1
                    y  = ty * 8 + row

                    if p0 != 0:
                        area += 1
                        if x0 < minx: minx = x0
                        if y  < miny: miny = y
                        if x0 > maxx: maxx = x0
                        if y  > maxy: maxy = y
                    if p1 != 0:
                        area += 1
                        if x1 < minx: minx = x1
                        if y  < miny: miny = y
                        if x1 > maxx: maxx = x1
                        if y  > maxy: maxy = y

    if area == 0:
        return None
    bbox_w = (maxx - minx + 1)
    bbox_h = (maxy - miny + 1)
    return bbox_w, bbox_h, area

# Resolve a frontPic symbol to a graphics file path by searching the repo for its definition line.
# We look for a quoted path on the same line or nearby (common in expansion tables).
def resolve_frontpic_file(front_sym: str) -> Path | None:
    # Fast search under src/ first, then full repo.
    lines = run_rg(rf"\b{re.escape(front_sym)}\b", "src")
    if not lines:
        lines = run_rg(rf"\b{re.escape(front_sym)}\b", ".")

    # Look for "graphics/...front.4bpp" or any quoted graphics path
    for ln in lines:
        m = re.search(r'"([^"]+graphics[^"]+)"', ln)
        if m:
            p = Path(m.group(1))
            if p.exists():
                return p
            # sometimes paths are relative (e.g. graphics/...)
            p2 = Path(m.group(1).lstrip("/"))
            if p2.exists():
                return p2

    # If not found inline, try a second-pass: find definition file then scan a few lines around it.
    # Parse "file:line:..." from rg output
    for ln in lines:
        parts = ln.split(":", 2)
        if len(parts) < 3:
            continue
        f = Path(parts[0])
        if not f.exists():
            continue
        try:
            lno = int(parts[1])
        except:
            continue
        content = f.read_text(encoding="utf-8", errors="ignore").splitlines()
        lo = max(0, lno - 8)
        hi = min(len(content), lno + 8)
        window = "\n".join(content[lo:hi])
        m = re.search(r'"([^"]+graphics[^"]+)"', window)
        if m:
            p = Path(m.group(1))
            if p.exists():
                return p
            p2 = Path(m.group(1).lstrip("/"))
            if p2.exists():
                return p2

    return None

# ------------------ parse species blocks ------------------

block_start = re.compile(r'^\s*\[\s*(SPECIES_[A-Z0-9_]+_SPACEWORLD)\s*\]\s*=\s*$', re.M)
starts = [(m.start(), m.end(), m.group(1)) for m in block_start.finditer(txt)]
seen = {}
for s,e,sy in starts:
    seen.setdefault(sy,(s,e,sy))
starts = sorted(seen.values(), key=lambda t:t[0])

re_height = re.compile(r'^\s*\.height\s*=\s*([0-9]+)\s*,', re.M)
re_weight = re.compile(r'^\s*\.weight\s*=\s*([0-9]+)\s*,', re.M)
re_front  = re.compile(r'^\s*\.frontPic\s*=\s*([A-Za-z0-9_]+)\s*,', re.M)

known = []   # (bbox_h, area, height, weight)
targets = [] # (species, front_sym, has_height, has_weight)

unresolved = []

for i,(s,e,sy) in enumerate(starts):
    nxt = starts[i+1][0] if i+1 < len(starts) else len(txt)
    block = txt[e:nxt]

    mfront = re_front.search(block)
    if not mfront:
        continue
    front_sym = mfront.group(1)

    mh = re_height.search(block)
    mw = re_weight.search(block)

    gfx_path = resolve_frontpic_file(front_sym)
    if gfx_path is None:
        unresolved.append((sy, front_sym))
        continue

    data = gfx_path.read_bytes()
    if gfx_path.suffix == ".lz" or gfx_path.name.endswith(".lz"):
        data = gba_lz77_decompress(data)

    met = frontpic_metrics_from_4bpp(data, size_px=64)
    if met is None:
        unresolved.append((sy, front_sym))
        continue

    bbox_w, bbox_h, area = met

    if mh and mw:
        known.append((bbox_h, area, int(mh.group(1)), int(mw.group(1))))
    else:
        targets.append((sy, front_sym, mh is not None, mw is not None, bbox_h, area))

print(f"Resolvable sprites w/ known hw pairs: {len(known)}")
print(f"Resolvable sprites missing hw:        {len(targets)}")
print(f"Unresolved frontPic symbols:          {len(unresolved)}")

if len(known) < 20:
    print("ERROR: too few known pairs. This usually means resolve_frontpic_file() isn't finding the graphics paths.")
    print("Try: rg -n \"<one frontPic symbol>\" src | head")
    # Show a few to help you debug quickly
    for sy, fs in unresolved[:10]:
        print("  unresolved:", sy, fs)
    sys.exit(2)

# Fit models
x_h = [k[0] for k in known]
y_h = [k[2] for k in known]
a_h, b_h = linfit(x_h, y_h)

x_w = [k[1] for k in known]
y_w = [k[3] for k in known]
a_w, b_w = linfit(x_w, y_w)

print(f"Height fit: height ≈ {a_h:.4f} * bbox_h + {b_h:.2f}")
print(f"Weight fit: weight ≈ {a_w:.6f} * area   + {b_w:.2f}")

# Predict
pred = {}
for sy, front_sym, has_h, has_w, bbox_h, area in targets:
    ph = a_h*bbox_h + b_h
    pw = a_w*area   + b_w
    ph_i = clamp_int(round(ph), 1, 3000)
    pw_i = clamp_int(round(pw), 1, 99999)
    pred[sy] = (ph_i, pw_i)

# Patch: insert missing .height/.weight before closing brace
patched = 0

def patch_block(block: str, sy: str) -> str:
    mh = re_height.search(block)
    mw = re_weight.search(block)
    need_h = mh is None
    need_w = mw is None
    if not (need_h or need_w):
        return block
    if sy not in pred:
        return block

    mclose = None
    for m in re.finditer(r'^\s*\},\s*$', block, re.M):
        mclose = m
    if not mclose:
        return block

    h_i, w_i = pred[sy]
    ins = ""
    if need_h:
        ins += f"    .height = {h_i}, // approx from frontPic 4bpp\n"
    if need_w:
        ins += f"    .weight = {w_i}, // approx from frontPic 4bpp\n"
    return block[:mclose.start()] + ins + block[mclose.start():]

out = []
pos = 0
for i,(s,e,sy) in enumerate(starts):
    nxt = starts[i+1][0] if i+1 < len(starts) else len(txt)
    out.append(txt[pos:e])
    block = txt[e:nxt]
    new_block = patch_block(block, sy)
    if new_block != block:
        patched += 1
    out.append(new_block)
    pos = nxt
out.append(txt[pos:])

OUT_H.write_text("".join(out), encoding="utf-8")
print(f"Patched species blocks: {patched}")
print(f"Wrote: {OUT_H}")
PY
