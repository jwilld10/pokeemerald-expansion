#!/usr/bin/env bash
set -euo pipefail

IN_FAMILIES="src/data/pokemon/species_info/bw3g_families.h"
OUT="src/data/pokemon/level_up_learnsets_bw3g.h"

[[ -f "$IN_FAMILIES" ]] || { echo "ERROR: missing $IN_FAMILIES" >&2; exit 1; }
mkdir -p "$(dirname "$OUT")"

python3 - <<'PY'
from pathlib import Path
import re

in_path = Path("src/data/pokemon/species_info/bw3g_families.h")
out_path = Path("src/data/pokemon/level_up_learnsets_bw3g.h")

txt = in_path.read_text(encoding="utf-8", errors="ignore")

# capture: .levelUpLearnset = SYMBOL,
pat = re.compile(r'\.levelUpLearnset\s*=\s*([A-Za-z0-9_]+)\s*,')
syms = sorted(set(pat.findall(txt)))

if not syms:
    raise SystemExit("ERROR: No .levelUpLearnset symbols found in bw3g_families.h")

guard = "GUARD_LEVEL_UP_LEARNSETS_BW3G_H"
lines = []
lines.append(f"#ifndef {guard}\n#define {guard}\n\n")
lines.append('#include "constants/moves.h"\n')
lines.append('#include "constants/pokemon.h"\n')
lines.append('#include "pokemon.h"\n\n')
lines.append("// Auto-generated stub learnsets for BW3G.\n")
lines.append("// These are intentionally minimal so the project compiles.\n")
lines.append("// Replace with real learnsets when you import them.\n\n")

# A safe one-move learnset to avoid 0-length edge cases
lines.append("static const struct LevelUpMove sBw3gStubLevelUpLearnset[] =\n{\n")
lines.append("    LEVEL_UP_MOVE(1, MOVE_TACKLE),\n")
lines.append("    LEVEL_UP_END\n};\n\n")

for s in syms:
    # If something already exists elsewhere, we don't want duplicate symbol errors.
    # But since this header is included into a TU, duplicates WILL break builds.
    # So we only emit `static const ...` which is TU-local.
    lines.append(f"static const struct LevelUpMove {s}[] =\n{{\n")
    lines.append("    LEVEL_UP_MOVE(1, MOVE_TACKLE),\n")
    lines.append("    LEVEL_UP_END\n};\n\n")

lines.append(f"#endif // {guard}\n")

out_path.write_text("".join(lines), encoding="utf-8")
print(f"Wrote {out_path} with {len(syms)} stub learnsets.")
PY
