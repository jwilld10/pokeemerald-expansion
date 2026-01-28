#!/usr/bin/env python3
from pathlib import Path
from collections import Counter

# Edit these if needed
ICON_DIRS = [
    Path("graphics/spaceworld/icons"),
    # If you have any other 32x32 icon sources you’re actually using at runtime, add them here
]

# Canonical meaning we want everywhere:
# 0 = transparent, 1 = orange, 2 = black (outline), 3 = red (fill)
CANON = {"accent": 1, "outline": 2, "fill": 3}

W, H = 32, 32
FRAME_BYTES = W * H // 2
FRAMES = 2
TOTAL_BYTES = FRAME_BYTES * FRAMES

def read_indices(buf, frame):
    off = frame * FRAME_BYTES
    fb = buf[off:off + FRAME_BYTES]
    idx = [0] * (W * H)
    p = 0
    for b in fb:
        idx[p]   = b & 0xF
        idx[p+1] = (b >> 4) & 0xF
        p += 2
    return idx

def write_indices(frames_idx):
    out = bytearray(TOTAL_BYTES)
    for f in range(FRAMES):
        idx = frames_idx[f]
        off = f * FRAME_BYTES
        p = 0
        for i in range(0, W * H, 2):
            lo = idx[i] & 0xF
            hi = idx[i+1] & 0xF
            out[off + p] = lo | (hi << 4)
            p += 1
    return bytes(out)

def bbox_of_nonzero(idx):
    xs, ys = [], []
    for y in range(H):
        for x in range(W):
            if idx[y*W + x] != 0:
                xs.append(x); ys.append(y)
    if not xs:
        return (0, 0, W-1, H-1)
    return (min(xs), min(ys), max(xs), max(ys))

def edge_counts(idx, bbox, thickness=1):
    x0,y0,x1,y1 = bbox
    c = Counter()
    for t in range(thickness):
        yt = y0 + t
        yb = y1 - t
        for x in range(x0, x1+1):
            c[idx[yt*W + x]] += 1
            c[idx[yb*W + x]] += 1
        xl = x0 + t
        xr = x1 - t
        for y in range(y0, y1+1):
            c[idx[y*W + xl]] += 1
            c[idx[y*W + xr]] += 1
    return c

def interior_counts(idx, bbox, margin=2):
    x0,y0,x1,y1 = bbox
    x0i = min(x1, x0 + margin)
    y0i = min(y1, y0 + margin)
    x1i = max(x0, x1 - margin)
    y1i = max(y0, y1 - margin)
    c = Counter()
    for y in range(y0i, y1i+1):
        for x in range(x0i, x1i+1):
            c[idx[y*W + x]] += 1
    return c

def detect_roles(idx):
    used = sorted(set(idx) - {0})
    counts = Counter(v for v in idx if v != 0)

    if not used:
        return None

    bbox = bbox_of_nonzero(idx)

    # Guess outline by what appears most on the bbox edge
    ec = edge_counts(idx, bbox, thickness=1)
    ec.pop(0, None)
    outline = ec.most_common(1)[0][0] if ec else used[0]

    # Guess fill by most common interior (excluding 0)
    ic = interior_counts(idx, bbox, margin=2)
    ic.pop(0, None)
    fill = ic.most_common(1)[0][0] if ic else counts.most_common(1)[0][0]

    # Accent is “the remaining nonzero” if present
    accent = None
    for u in used:
        if u not in (outline, fill):
            accent = u
            break

    # If fill==outline (can happen), fall back to global nonzero frequency for fill
    if fill == outline:
        for u, _ in counts.most_common():
            if u != outline:
                fill = u
                break

    # Recompute accent if needed
    if accent is None:
        for u in used:
            if u not in (outline, fill):
                accent = u
                break

    return {"outline": outline, "fill": fill, "accent": accent, "used": used, "counts": dict(counts)}

def remap_frame(idx, mapping):
    # mapping: old_index -> new_index
    out = idx[:]
    for i, v in enumerate(out):
        out[i] = mapping.get(v, v)
    return out

def make_role_to_role_remap(src_roles, dst_roles):
    # remap indices so src frame matches dst frame roles (to stop flashing)
    m = {0: 0}
    # Map outline/fill/accent when they exist in both
    for role in ("outline", "fill", "accent"):
        s = src_roles.get(role)
        d = dst_roles.get(role)
        if s is not None and d is not None:
            m[s] = d
    return m

def make_to_canonical_remap(roles):
    # remap indices so roles match canonical indices
    m = {0: 0}
    if roles["outline"] is not None:
        m[roles["outline"]] = CANON["outline"]
    if roles["fill"] is not None:
        m[roles["fill"]] = CANON["fill"]
    if roles["accent"] is not None:
        m[roles["accent"]] = CANON["accent"]
    return m

def process_file(p: Path):
    buf = p.read_bytes()
    if len(buf) != TOTAL_BYTES:
        return (False, f"SKIP (size {len(buf)} not 1024)")

    frames = [read_indices(buf, f) for f in range(FRAMES)]
    roles = [detect_roles(frames[f]) for f in range(FRAMES)]
    if roles[0] is None or roles[1] is None:
        return (False, "SKIP (no pixels?)")

    # Step A: stop flashing by making frame1 roles match frame0 roles
    m_flash = make_role_to_role_remap(roles[1], roles[0])
    frames[1] = remap_frame(frames[1], m_flash)
    roles[1] = detect_roles(frames[1])

    # Step B: map both frames to canonical indices
    m0 = make_to_canonical_remap(roles[0])
    m1 = make_to_canonical_remap(roles[1])
    frames[0] = remap_frame(frames[0], m0)
    frames[1] = remap_frame(frames[1], m1)

    newbuf = write_indices(frames)
    if newbuf == buf:
        return (False, "OK (no change)")

    # backup once
    bak = p.with_suffix(p.suffix + ".bak")
    if not bak.exists():
        bak.write_bytes(buf)
    p.write_bytes(newbuf)
    return (True, "PATCHED")

def main():
    patched = 0
    checked = 0
    for d in ICON_DIRS:
        for p in sorted(d.glob("*.4bpp")):
            checked += 1
            changed, msg = process_file(p)
            if changed:
                patched += 1
            # Print only interesting ones to keep output sane
            if changed:
                print(f"{msg:7} {p}")
    print(f"\nDone. checked={checked} patched={patched}")

if __name__ == "__main__":
    main()
