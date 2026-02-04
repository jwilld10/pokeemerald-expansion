#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:?usage: $0 /path/to/pokegold-spaceworld}"
ROOT="$(realpath "$ROOT")"

DEX="$ROOT/data/pokemon/dex_entries.asm"
[[ -f "$DEX" ]] || { echo "ERROR: missing $DEX" >&2; exit 1; }

missing=(
  BELLRUN BELMITT BOMSHEAL CORASUN CRUIZE ELEBABE GELANIA GUPGOLD KURSTRAW METTO
  NYANYA PANGSHI PARAMITE PETAMOLE PETICORN PRAXE PUDDIPUP TANGTRIP TRIPSTAR
)

echo "ROOT: $ROOT"
echo "DEX:  $DEX"
echo

# Grab all DexEntry labels and pointer table refs for quick membership tests.
tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

rg -n '^\s*[A-Za-z0-9_]+DexEntry:\s*$' "$DEX" \
  | sed -E 's/^\s*([A-Za-z0-9_]+DexEntry):.*/\1/' \
  | sort -u > "$tmpdir/labels.txt"

rg -n '^\s*dw\s+[A-Za-z0-9_]+DexEntry\s*$' "$DEX" \
  | awk '{print $2}' \
  | sort -u > "$tmpdir/pointers.txt"

echo "DexEntry labels found:   $(wc -l < "$tmpdir/labels.txt" | tr -d ' ')"
echo "Pointer refs found:     $(wc -l < "$tmpdir/pointers.txt" | tr -d ' ')"
echo

echo "== Check each missing mon =="
for m in "${missing[@]}"; do
  # common guess label spellings
  # - TitleCase: BELLRUN -> BellrunDexEntry
  # - Uppercase (rare): BELLRUN -> BELLRUNDexEntry
  # - Weird special-cases:
  #   FARFETCH_D would be FarfetchdDexEntry; MR_MIME -> MrMimeDexEntry; HO_OH -> HoOhDexEntry; NIDORAN_F -> NidoranFDexEntry
  title="$(echo "$m" | awk '{print tolower($0)}' | sed -E 's/(^|_)([a-z])/\U\2/g; s/_//g')"
  cand1="${title}DexEntry"
  cand2="${m}DexEntry"

  in_labels="no"
  in_ptrs="no"

  if rg -q "^${cand1}\$" "$tmpdir/labels.txt" || rg -q "^${cand2}\$" "$tmpdir/labels.txt"; then
    in_labels="YES"
  fi
  if rg -q "^${cand1}\$" "$tmpdir/pointers.txt" || rg -q "^${cand2}\$" "$tmpdir/pointers.txt"; then
    in_ptrs="YES"
  fi

  echo "-- $m"
  echo "   label candidate:   $cand1  (or $cand2)"
  echo "   exists as label?:  $in_labels"
  echo "   in pointers?:      $in_ptrs"

  # Also check for DEX_* constants anywhere (helps confirm it is “a thing” in this repo)
  # (this search is cheap; it’s just a hint)
  if rg -n --hidden --no-ignore-vcs -S "DEX_${m}\b" "$ROOT" >/dev/null 2>&1; then
    hit="$(rg -n --hidden --no-ignore-vcs -S "DEX_${m}\b" "$ROOT" | head -n 1)"
    echo "   has DEX_ const?:   YES ($hit)"
  else
    echo "   has DEX_ const?:   no"
  fi
done

echo
echo "Tip: if exists-as-label=YES but in-pointers=no, it means a DexEntry block exists but isn't actually used in the pokedex list."
