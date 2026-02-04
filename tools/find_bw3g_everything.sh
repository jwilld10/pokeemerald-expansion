#!/bin/sh
set -eu

echo "=== BW3G: files that exist ==="
find src include graphics tools -type f \( -iname '*bw3g*' -o -iname '*genesis*' \) -print | sort

echo
echo "=== BW3G: any mention of SPECIES_*_BW3G anywhere ==="
rg -n "SPECIES_[A-Z0-9_]+_BW3G" -S src include tools | head -n 200 || true

echo
echo "=== BW3G: any species-info style fields near BW3G tokens ==="
rg -n "BW3G.*\.baseHP|\.baseHP.*BW3G|BW3G.*baseHP" -S src include tools || true

echo
echo "=== CSV / mapping sources present? ==="
ls -lah bw3g_*.csv bw3g_*.txt 2>/dev/null || true
