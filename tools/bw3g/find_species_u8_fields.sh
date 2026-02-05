#!/usr/bin/env bash
set -e

cd ~/decomps/pokeemerald-expansion_clean

echo "===== Searching for u8 species storage ====="
echo

rg -n "u8.*species" src include || true

echo
echo "===== Searching struct members named species ====="
echo

rg -n "species;" src include || true

echo
echo "===== Searching SetMonData / CreateMon usage ====="
echo

rg -n "SetMonData.*SPECIES" src || true
rg -n "CreateMon(" src || true

echo
echo "===== Searching ScriptGiveMon pipeline ====="
echo

rg -n "ScriptGiveMon" -n src || true

echo
echo "DONE"
