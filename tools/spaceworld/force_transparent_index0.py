#!/usr/bin/env python3
import argparse
from pathlib import Path
from PIL import Image

def force_index0(p: Path, apply: bool) -> bool:
    im = Image.open(p)

    # Must be paletted
    if im.mode != "P":
        # Convert to P without changing visible colors:
        # If it has alpha, convert via RGBA -> P is dangerous (quantize).
        # So we refuse here to avoid recoloring.
        raise SystemExit(f"ERROR: {p}: not PNG8 (mode P). Refusing to quantize/recolor.")

    # Pillow stores transparency as either info['transparency'] (single index) or bytes
    tr = im.info.get("transparency", None)

    if tr is None:
        # No transparency metadata. Still might have "background index" usage,
        # but we won't guess. This is likely the root of your black box.
        raise SystemExit(f"ERROR: {p}: no transparency chunk. Need a transparency index to move to 0.")

    if isinstance(tr, int):
        trans_idx = tr
    else:
        # If it's a bytes table, treat 0-alpha entries as transparent.
        # pick first fully transparent index
        trans_idx = None
        for i, a in enumerate(tr):
            if a == 0:
                trans_idx = i
                break
        if trans_idx is None:
            raise SystemExit(f"ERROR: {p}: transparency table exists but no fully transparent entry.")

    if trans_idx == 0:
        return False  # already correct

    # Remap pixel indices: swap trans_idx <-> 0
    data = bytearray(im.tobytes())
    for i, v in enumerate(data):
        if v == 0:
            data[i] = trans_idx
        elif v == trans_idx:
            data[i] = 0

    # Swap palette entries in the palette table (RGB triples)
    pal = im.getpalette()
    if pal is None:
        raise SystemExit(f"ERROR: {p}: missing palette data.")

    def swap_triplet(arr, a, b):
        a3, b3 = a*3, b*3
        arr[a3:a3+3], arr[b3:b3+3] = arr[b3:b3+3], arr[a3:a3+3]

    swap_triplet(pal, 0, trans_idx)

    out = Image.frombytes("P", im.size, bytes(data))
    out.putpalette(pal)

    # Fix transparency metadata to index 0
    out.info["transparency"] = 0

    if apply:
        out.save(p)
    return True

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("png", help="Path to PNG8 summary sprite")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    p = Path(args.png)
    changed = force_index0(p, args.apply)
    print(f"{'APPLIED' if args.apply else 'DRY'}: {p} | transparency->index0 changed={int(changed)}")

if __name__ == "__main__":
    main()
