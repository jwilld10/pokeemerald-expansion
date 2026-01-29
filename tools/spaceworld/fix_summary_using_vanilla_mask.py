#!/usr/bin/env python3
import argparse
import os
from PIL import Image

def load_frame64(p: str) -> Image.Image:
    im = Image.open(p)
    if im.mode != "P":
        im = im.convert("P")
    w, h = im.size
    if (w, h) == (64, 64):
        return im
    if w == 64 and h >= 64:
        return im.crop((0, 0, 64, 64))
    raise ValueError(f"{p}: expected P 64x64 or 64x(>=64), got {im.mode} {im.size}")

def flood_bg_mask(imP: Image.Image) -> list[bool]:
    px = imP.load()
    bg = px[0, 0]
    W, H = imP.size
    seen = [[False]*W for _ in range(H)]
    stack = [(0,0)]
    seen[0][0] = True
    while stack:
        x,y = stack.pop()
        for nx, ny in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
            if 0 <= nx < W and 0 <= ny < H and not seen[ny][nx] and px[nx,ny] == bg:
                seen[ny][nx] = True
                stack.append((nx,ny))
    return [seen[y][x] for y in range(H) for x in range(W)]

def ensure_index0_transparent(imP: Image.Image) -> Image.Image:
    imP = imP.copy()
    px = imP.load()

    t = imP.info.get("transparency", None)
    if t == 0:
        return imP

    if isinstance(t, int):
        src = t
        if src != 0:
            for y in range(64):
                for x in range(64):
                    v = px[x,y]
                    if v == 0:
                        px[x,y] = src
                    elif v == src:
                        px[x,y] = 0
            pal = imP.getpalette()
            for c in range(3):
                pal[0*3+c], pal[src*3+c] = pal[src*3+c], pal[0*3+c]
            imP.putpalette(pal)
        imP.info["transparency"] = 0
        return imP

    imP.info["transparency"] = 0
    return imP

def apply_mask(space: Image.Image, mask_bg: list[bool]) -> tuple[Image.Image,int]:
    out = space.copy()
    px = out.load()
    changed = 0
    i = 0
    for y in range(64):
        for x in range(64):
            if mask_bg[i]:
                if px[x,y] != 0:
                    px[x,y] = 0
                    changed += 1
            i += 1
    out = ensure_index0_transparent(out)
    return out, changed

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("space_png")
    ap.add_argument("--vanilla-root", default="graphics/pokemon")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    space_path = args.space_png
    parts = space_path.replace("\\","/").split("/")
    try:
        species = parts[parts.index("pokemon")+1]
        fname = parts[-1]
    except Exception:
        raise SystemExit(f"Can't parse species from: {space_path}")

    vanilla_path = os.path.join(args.vanilla_root, species, fname)
    if not os.path.exists(vanilla_path):
        print(f"SKIP: {space_path} (no vanilla ref: {vanilla_path})")
        return 0

    space = load_frame64(space_path)
    vanilla = load_frame64(vanilla_path)

    mask_bg = flood_bg_mask(vanilla)
    fixed, changed = apply_mask(space, mask_bg)

    if args.apply:
        fixed.save(space_path, optimize=False)
        print(f"APPLIED: {space_path} | bgmask->idx0 changed_px={changed} | vanilla_ref={vanilla_path}")
    else:
        print(f"DRY: {space_path} | would_change_px={changed} | vanilla_ref={vanilla_path}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
