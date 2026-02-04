#!/usr/bin/env bash
set -euo pipefail

BW3G_ROOT="${1:-$HOME/decomps/gb/BW3G}"
BW3G_ROOT="$(realpath "$BW3G_ROOT")"

if [[ ! -d "$BW3G_ROOT" ]]; then
  echo "ERROR: BW3G root not found: $BW3G_ROOT" >&2
  exit 1
fi

MAX="${MAX_RESULTS:-400}"
OUT="bw3g_table_finder_$(date +%Y%m%d_%H%M%S).txt"

{
  echo "BW3G ROOT: $BW3G_ROOT"
  echo "MAX_RESULTS: $MAX"
  echo

  echo "== Candidates: base stats =="
  rg -n --hidden --no-ignore-vcs -S \
    "(base[_ ]?stats|BaseStats|hp[, ]+atk|atk[, ]+def|SpAtk|SpDef|catch rate|exp yield|EXP_YIELD|CATCH_RATE)" \
    "$BW3G_ROOT" 2>/dev/null | head -n "$MAX" || true
  echo

  echo "== Candidates: evos/learnsets (evos_attacks etc) =="
  rg -n --hidden --no-ignore-vcs -S \
    "(evos[_ ]?attacks|EvosAttacks|evos_attacks|learnset|level[_ ]?up|moves at|dbw|db\s+[0-9]+,\s*MOVE_|MOVE_[A-Z0-9_]+)" \
    "$BW3G_ROOT" 2>/dev/null | head -n "$MAX" || true
  echo

  echo "== Candidates: pokedex entries (text/height/weight/category) =="
  rg -n --hidden --no-ignore-vcs -S \
    "(dex entry|dex_entry|PokedexEntry|pokedex entry|pokedex_entries|dex_entries|dex text|dex_text|species category|category|height|weight|FT|LB|HT|WT)" \
    "$BW3G_ROOT" 2>/dev/null | head -n "$MAX" || true
  echo

  echo "== Candidates: species/names (name tables) =="
  rg -n --hidden --no-ignore-vcs -S \
    "(species names|SpeciesNames|PokemonNames|MON_NAMES|db\s+\"[A-Z0-9 ?!'.-]+\"|NAME_)" \
    "$BW3G_ROOT" 2>/dev/null | head -n "$MAX" || true
  echo

  echo "== Candidates: cries =="
  rg -n --hidden --no-ignore-vcs -S \
    "(cry|Cries|PokemonCries|SFX_CRY|CRY_[A-Z0-9_]+)" \
    "$BW3G_ROOT" 2>/dev/null | head -n "$MAX" || true
  echo

  echo "== File list shortcuts (common GB layouts) =="
  find "$BW3G_ROOT" -maxdepth 8 -type f \( \
    -iname "*base_stats*" -o -iname "*evos_attacks*" -o -iname "*dex*" -o -iname "*cries*" -o \
    -iname "*pokedex*" -o -iname "*pokemon_names*" -o -iname "*mon_names*" -o -iname "*species_names*" \
  \) 2>/dev/null | sort || true
  echo

  echo "WROTE: $OUT"
} > "$OUT"

echo "WROTE: $OUT"
