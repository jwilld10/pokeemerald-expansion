#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import textwrap
from pathlib import Path
from typing import Optional

BW3G_ROOT = Path.home() / "decomps/gb/BW3G"

SPECIES_HDR = Path("include/constants/species_bw3g.h")
OUT_HDR = Path("include/data/pokemon/bw3g_generated/bw3g_pokedex_text.h")

# --- helpers ---------------------------------------------------------------

def canon(token: str) -> str:
    s = token.lower()
    s = s.replace("ho_oh", "hooh")
    s = s.replace("mr_mime", "mrmime")
    s = s.replace("mime_jr", "mimejr")
    s = s.replace("porygon_z", "porygonz")
    s = s.replace("nidoran_f", "nidoranf")
    s = s.replace("nidoran_m", "nidoranm")
    return s

def c_escape(s: str) -> str:
    # C string escaping for _("...")
    s = s.replace("\\", "\\\\").replace('"', '\\"')
    return s

def wrap_underscore_string(s: str, width: int = 68) -> str:
    # Wrap long text into adjacent C string literals inside _("...")
    # _("foo" "bar")
    s = s.strip()
    if not s:
        return '_("")'
    wrapped = textwrap.wrap(s, width=width, break_long_words=False, break_on_hyphens=False)
    parts = "".join([f'\n    "{c_escape(line)}"' for line in wrapped])
    return f'_({parts}\n)'

def parse_bw3g_species_order() -> list[tuple[str, str]]:
    """
    Returns [(SPECIES_FOO_BW3G, foo), ...] in header order.
    Works with your macro style: #define SPECIES_SNIVY_BW3G (SPECIES_ZUBAT_SPACEWORLD + 1)
    """
    lines = SPECIES_HDR.read_text(encoding="utf-8", errors="replace").splitlines()
    out: list[tuple[str, str]] = []
    rx = re.compile(r'^\s*#define\s+(SPECIES_([A-Z0-9_]+)_BW3G)\b')
    for ln in lines:
        m = rx.match(ln)
        if m:
            out.append((m.group(1), m.group(2)))
    if not out:
        raise SystemExit(f"ERROR: no BW3G species parsed from {SPECIES_HDR}")
    return out

# --- source 1: BW3G local files -------------------------------------------

def find_bw3g_dex_sources() -> list[Path]:
    if not BW3G_ROOT.exists():
        return []
    pats = ["*pokedex*entry*", "*pokedex*", "*dex*entry*", "*dex_entries*"]
    exts = {".json", ".txt", ".inc", ".asm", ".h", ".csv"}
    hits: list[Path] = []
    for pat in pats:
        for p in BW3G_ROOT.rglob(pat):
            if p.is_file() and p.suffix.lower() in exts:
                hits.append(p)
    # Prefer more “structured” formats first
    hits.sort(key=lambda p: (p.suffix.lower() not in {".json", ".csv"}, len(str(p))))
    return hits[:25]

def load_bw3g_entries_from_json(p: Path) -> Optional[dict[str, str]]:
    """
    Attempts to interpret a JSON file as a mapping of name->entry.
    Supports:
      - {"snivy": "text", ...}
      - [{"name":"snivy","entry":"text"}, ...]
      - {"pokemon":[{"name":"snivy","entry":"text"}]}
    """
    try:
        data = json.loads(p.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return None

    out: dict[str, str] = {}

    if isinstance(data, dict):
        # direct dict mapping?
        if all(isinstance(k, str) and isinstance(v, str) for k, v in data.items()):
            for k, v in data.items():
                out[canon(k)] = v
            return out

        # nested list?
        for key in ("pokemon", "entries", "pokedex", "dex"):
            if key in data and isinstance(data[key], list):
                arr = data[key]
                for item in arr:
                    if isinstance(item, dict):
                        name = item.get("name") or item.get("species")
                        entry = item.get("entry") or item.get("text") or item.get("flavor")
                        if isinstance(name, str) and isinstance(entry, str):
                            out[canon(name)] = entry
                if out:
                    return out

    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                name = item.get("name") or item.get("species")
                entry = item.get("entry") or item.get("text") or item.get("flavor")
                if isinstance(name, str) and isinstance(entry, str):
                    out[canon(name)] = entry
        if out:
            return out

    return None

def load_bw3g_entries_best_effort() -> dict[str, str]:
    """
    Try to find BW3G-provided dex text.
    If we can't parse anything confidently, return {} and let PokéAPI handle it.
    """
    srcs = find_bw3g_dex_sources()
    for p in srcs:
        if p.suffix.lower() == ".json":
            got = load_bw3g_entries_from_json(p)
            if got:
                print(f"[BW3G] Using JSON dex source: {p}")
                return got
    # You can extend here for .asm/.inc patterns once you identify BW3G’s format.
    return {}

# --- output ----------------------------------------------------------------

def main() -> None:
    species = parse_bw3g_species_order()

    OUT_HDR.parent.mkdir(parents=True, exist_ok=True)

    # Try BW3G local first
    local = load_bw3g_entries_best_effort()

    # If local is empty, use PokéAPI
    use_api = (len(local) == 0)

    if use_api:
        try:
            import requests  # noqa
        except Exception:
            raise SystemExit(
                "ERROR: PokéAPI mode needs python package 'requests'.\n"
                "Install it:  python3 -m pip install --user requests"
            )
        print("[SRC] BW3G dex text not found/parsed -> using PokéAPI (real official entries).")
    else:
        print(f"[SRC] Using BW3G-provided dex entries: {len(local)} parsed")

    # Build content
    arrays: list[str] = []
    table: list[str] = []

    missing: list[str] = []

    for full, tok in species:
        name = canon(tok)

        # special-case your "genesis_mon" if PokéAPI doesn't have it
        api_name = name
        if api_name == "genesis_mon":
            api_name = "genesect"

        text = local.get(name)
        if not text and use_api:
            text = fetch_pokeapi_entry(api_name)

        if not text:
            missing.append(name)
            # still "real" requirement: if truly missing, hard fail
            raise SystemExit(f"ERROR: Could not get real dex entry for: {name}")

        sym = f"sBw3gDexText_{tok}"
        arrays.append(f"static const u8 {sym}[] = {wrap_underscore_string(text)};\n")
        table.append(f"    [{full} - SPECIES_SNIVY_BW3G] = {sym},")

    out = []
    out.append("// Auto-generated. Do not edit.\n")
    out.append("#ifndef GUARD_BW3G_POKEDEX_TEXT_H\n#define GUARD_BW3G_POKEDEX_TEXT_H\n\n")
    out.append('#include "global.h"\n')
    out.append('#include "constants/species_bw3g.h"\n\n')

    out.append("// Dex text arrays (UTF-8 converted via _())\n\n")
    out.extend(arrays)

    out.append("\n// Pointer table indexed by (species - SPECIES_SNIVY_BW3G)\n")
    out.append("static const u8 *const gBw3gPokedexTextPointers[] =\n{\n")
    out.append("\n".join(table))
    out.append("\n};\n\n")

    out.append("#endif // GUARD_BW3G_POKEDEX_TEXT_H\n")

    OUT_HDR.write_text("".join(out), encoding="utf-8")

    print(f"[OK] Wrote: {OUT_HDR} (entries: {len(species)})")
    if missing:
        print(f"[WARN] Missing entries: {len(missing)} (should be 0 because we hard-fail)")

if __name__ == "__main__":
    main()
