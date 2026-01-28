#!/usr/bin/env python3
from pathlib import Path
from collections import Counter
from datetime import datetime

W, H = 32, 64
FRAME_H = 32
PRESERVE = 4

def read_icon(p):
    d = p.read_bytes()
    px = [[0]*W for _ in range(H)]
    o = 0
    for ty in range(8):
        for tx in range(4):
            t = d[o:o+32]; o+=32
            for r in range(8):
                y = ty*8+r
                x = tx*8
                for i,b in enumerate(t[r*4:(r+1)*4]):
                    px[y][x+i*2]   = b & 0xF
                    px[y][x+i*2+1] = b>>4 & 0xF
    return px

def write_icon(p, px):
    out = bytearray()
    for ty in range(8):
        for tx in range(4):
            for r in range(8):
                y = ty*8+r
                x = tx*8
                for i in range(0,8,2):
                    out.append(px[y][x+i] | (px[y][x+i+1]<<4))
    p.write_bytes(out)

def boundary(mask):
    out=[]
    for y in range(32):
        for x in range(32):
            if not mask[y][x]: continue
            for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
                nx,ny=x+dx,y+dy
                if nx<0 or ny<0 or nx>=32 or ny>=32 or not mask[ny][nx]:
                    out.append((x,y))
                    break
    return out

def fix_frame(f):
    mask=[[v!=0 for v in row] for row in f]
    b=boundary(mask)
    if len(b)<10: return False
    bc=Counter(f[y][x] for x,y in b if f[y][x] not in (0,PRESERVE))
    if not bc: return False
    outline=bc.most_common(1)[0][0]
    ic=Counter(v for row in f for v in row if v not in (0,PRESERVE))
    fill=[k for k,_ in ic.most_common() if k!=outline]
    if not fill: return False
    fill=fill[0]
    accent=[k for k,_ in ic.most_common() if k not in (outline,fill)]
    accent=accent[0] if accent else None
    mapping={outline:2, fill:1}
    if accent: mapping[accent]=3
    for y in range(32):
        for x in range(32):
            v=f[y][x]
            if v in mapping: f[y][x]=mapping[v]
    return True

icons=Path("graphics/spaceworld/icons")
backup=icons.parent/f"_icon_backups_v2_{datetime.now():%Y%m%d_%H%M%S}"
backup.mkdir(parents=True)

fixed=0
for p in icons.glob("*.4bpp"):
    px=read_icon(p)
    changed=False
    for i in (0,1):
        fr=px[i*32:(i+1)*32]
        if fix_frame(fr):
            px[i*32:(i+1)*32]=fr
            changed=True
    if changed:
        backup.joinpath(p.name).write_bytes(p.read_bytes())
        write_icon(p,px)
        fixed+=1
        print("FIX",p.name)

print("Fixed",fixed,"icons")
print("Backups in",backup)
