#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import re
import sys

def bgr555(r: int, g: int, b: int) -> int:
    # clamp 0..31
    r = max(0, min(31, r))
    g = max(0, min(31, g))
    b = max(0, min(31, b))
    # GBA/GBC use BGR555 little-endian
    return (b << 10) | (g << 5) | r

def parse_text_pal(p: Path) -> list[int]:
    txt = p.read_text(encoding="utf-8", errors="replace")
    # Accept common formats:
    # - "RGB 31 0 0" per line
    # - "31 0 0" per line
    # - "JASC-PAL" blocks with 0..255
    lines = [ln.strip() for ln in txt.splitlines() if ln.strip() and not ln.strip().startswith(";")]

    if lines and lines[0].upper().startswith("JASC-PAL"):
        # JASC-PAL
        # line2: version, line3: count, then R G B 0..255
        if len(lines) < 4:
            raise ValueError(f"Bad JASC-PAL: {p}")
        count = int(lines[2])
        cols = []
        for ln in lines[3:3+count]:
            parts = ln.split()
            if len(parts) < 3:
                continue
            r8, g8, b8 = map(int, parts[:3])
            cols.append(bgr555(r8 * 31 // 255, g8 * 31 // 255, b8 * 31 // 255))
        return cols

    cols: list[int] = []
    for ln in lines:
        ln2 = ln.replace(",", " ")
        parts = ln2.split()
        if not parts:
            continue
        if parts[0].upper() == "RGB" and len(parts) >= 4:
            r, g, b = map(int, parts[1:4])
            cols.append(bgr555(r, g, b))
        elif len(parts) >= 3 and all(re.fullmatch(r"-?\d+", x) for x in parts[:3]):
            r, g, b = map(int, parts[:3])
            # If these look like 0..255, scale down
            if max(r, g, b) > 31:
                cols.append(bgr555(r * 31 // 255, g * 31 // 255, b * 31 // 255))
            else:
                cols.append(bgr555(r, g, b))

    if not cols:
        raise ValueError(f"Could not parse palette text: {p}")
    return cols

def parse_gbcpal_bin(p: Path) -> list[int]:
    data = p.read_bytes()
    if len(data) % 2 != 0:
        raise ValueError(f"gbcpal length not even: {p} ({len(data)})")
    cols = []
    for i in range(0, len(data), 2):
        cols.append(data[i] | (data[i+1] << 8))
    return cols

def write_gbapal(cols: list[int], outp: Path) -> None:
    # Ensure exactly 16 colors. Pad by repeating color 0 if needed.
    if len(cols) < 16:
        cols = cols + [cols[0]] * (16 - len(cols))
    cols = cols[:16]
    out = bytearray()
    for c in cols:
        out.append(c & 0xFF)
        out.append((c >> 8) & 0xFF)
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_bytes(bytes(out))

def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("Usage: convert_spaceworld_pal.py <in.pal|in.gbcpal> <out.gbapal>", file=sys.stderr)
        return 2
    inp = Path(argv[1])
    outp = Path(argv[2])
    if not inp.exists():
        print(f"Missing input: {inp}", file=sys.stderr)
        return 1

    if inp.suffix.lower() == ".gbcpal":
        cols = parse_gbcpal_bin(inp)
    else:
        cols = parse_text_pal(inp)

    write_gbapal(cols, outp)
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
