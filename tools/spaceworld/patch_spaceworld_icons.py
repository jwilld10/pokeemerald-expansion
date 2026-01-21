#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path

MENU_MAP = Path("tools/spaceworld_extracted/menu_icon_map.json")
TARGET   = Path("src/data/pokemon/spaceworld_generated/spaceworld_species_info.h")

# File species name -> menu_icon_map species name
ALIASES = {
    "BALLERINE": "MIMEJR",
    "GELANIA": "TANGROWTH",
    "TANGTRIP": "TANG",
    "PETAMOLE": "BLOSSOMOLE",
    "MEGANIUM": "BLOSSOMITE",
    "MR_MIME": "MR__MIME",  # your map uses double underscore
}

def icon_token_to_symbol(icon_token: str) -> str:
    # ICON_HO_OH -> gSwIcon_HoOh, ICON_MAIL_BIG -> gSwIcon_MailBig
    name = icon_token.removeprefix("ICON_").lower()
    parts = [p for p in name.split("_") if p]
    camel = "".join(p[:1].upper() + p[1:] for p in parts)
    return f"gSwIcon_{camel}"

def patch_body(body: str, icon_symbol: str) -> str:
    # Replace if present
    if re.search(r"^\s*\.iconSprite\s*=", body, flags=re.M):
        return re.sub(r"^\s*\.iconSprite\s*=\s*[^,]+,\s*$",
                      f"    .iconSprite = {icon_symbol},",
                      body, flags=re.M)

    # Otherwise insert near the end of the struct body (before footer "},")
    # Keep formatting clean: ensure body ends with newline
    if not body.endswith("\n"):
        body += "\n"
    return body + f"    .iconSprite = {icon_symbol},\n"

def main() -> None:
    if not MENU_MAP.exists():
        raise SystemExit(f"Missing {MENU_MAP} (run your extractor first).")
    if not TARGET.exists():
        raise SystemExit(f"Missing {TARGET}")

    mapping = json.loads(MENU_MAP.read_text(encoding="utf-8"))
    text = TARGET.read_text(encoding="utf-8")

    # Entry layout:
    # [SPECIES_FOO_SPACEWORLD] =
    # {
    #    ...body...
    # },
    entry_re = re.compile(
        r"(\[SPECIES_([A-Z0-9_]+)_SPACEWORLD\]\s*=\s*\{\n)(.*?)(^\s*\},\s*$)",
        flags=re.S | re.M
    )

    patched = 0
    missing_in_map = []

    def repl(m: re.Match) -> str:
        nonlocal patched
        header = m.group(1)
        symname = m.group(2)
        body = m.group(3)
        footer = m.group(4)

        key = symname
        if key not in mapping:
            # try alias
            key = ALIASES.get(symname, symname)

        if key not in mapping:
            missing_in_map.append(symname)
            return m.group(0)

        icon_token = mapping[key]
        icon_symbol = icon_token_to_symbol(icon_token)

        new_body = patch_body(body, icon_symbol)
        if new_body != body:
            patched += 1

        return header + new_body + footer

    new_text = entry_re.sub(repl, text)
    TARGET.write_text(new_text, encoding="utf-8")

    print(f"Patched entries: {patched}")
    if missing_in_map:
        print(f"WARNING: species in file but not in menu map ({len(missing_in_map)}). First 20: {missing_in_map[:20]}")
    print("Done.")

if __name__ == "__main__":
    main()
