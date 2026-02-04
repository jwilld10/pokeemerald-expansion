#!/usr/bin/env bash
set -euo pipefail

echo "== Checking if BW3G pic symbols exist =="

rg 'gMonFrontPic_.*Bw3g' src/bw3g_pokemon_pics.c | head -n 40
