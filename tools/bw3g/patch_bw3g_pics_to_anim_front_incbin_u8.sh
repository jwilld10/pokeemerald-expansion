#!/usr/bin/env bash
set -euo pipefail

C="src/bw3g_pokemon_pics.c"
H="include/data/pokemon/bw3g_generated/bw3g_pokemon_pics.h"

cp -a "$C" "$C.bak_animfront_$(date +%Y%m%d_%H%M%S)"
cp -a "$H" "$H.bak_animfront_$(date +%Y%m%d_%H%M%S)"

# 1) front -> anim_front path
perl -0777 -i -pe 's#("graphics/bw3g/pokemon/[^"]+/)front\.4bpp\.lz"#${1}anim_front.4bpp.lz"#g' "$C"

# 2) Make front/back arrays u8 + INCBIN_U8 (keep ALIGNED(4))
perl -0777 -i -pe '
s/ALIGNED\(4\)\s+const\s+u32\s+(gMonFrontPic_[A-Za-z0-9_]+Bw3g)\[\]\s*=\s*INCBIN_U32/ALIGNED(4) const u8 ${1}[] = INCBIN_U8/g;
s/ALIGNED\(4\)\s+const\s+u32\s+(gMonBackPic_[A-Za-z0-9_]+Bw3g)\[\]\s*=\s*INCBIN_U32/ALIGNED(4) const u8 ${1}[] = INCBIN_U8/g;
' "$C"

# 3) Header: declare these as u8 now (front/back)
perl -0777 -i -pe '
s/extern\s+const\s+u32\s+(gMonFrontPic_[A-Za-z0-9_]+Bw3g)\[\];/extern const u8 ${1}[];/g;
s/extern\s+const\s+u32\s+(gMonBackPic_[A-Za-z0-9_]+Bw3g)\[\];/extern const u8 ${1}[];/g;
' "$H"

echo "OK: patched to anim_front + INCBIN_U8 (u8 arrays)."
