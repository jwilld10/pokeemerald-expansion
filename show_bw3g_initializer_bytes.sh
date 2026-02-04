#!/usr/bin/env bash
set -euo pipefail

F="src/data/pokemon/species_info/bw3g_families.h"

echo "Showing first 15 lines containing 'SPECIES_' with nonprinting chars visible:"
echo "------------------------------------------------------------"
# Print lines with cat -A so hidden chars show as ^I, M-..., etc
rg -n 'SPECIES_.*_BW3G' "$F" | head -n 15 | cut -d: -f2- | cat -A
echo

echo "Now showing the raw byte values of the first 3 initializer lines (if any):"
echo "------------------------------------------------------------"
# Extract the first 3 lines that contain '[' and 'SPECIES_' and print their bytes
python3 - <<'PY'
import re
path = "src/data/pokemon/species_info/bw3g_families.h"
lines = []
with open(path, "rb") as f:
    for raw in f:
        if b"SPECIES_" in raw and b"[" in raw:
            lines.append(raw.rstrip(b"\n"))
        if len(lines) >= 3:
            break

for i, raw in enumerate(lines, 1):
    print(f"Line {i} bytes:", list(raw[:60]))
    print("As repr:", raw[:120])
    print()
PY
