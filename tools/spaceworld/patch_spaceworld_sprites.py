#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import re
import sys

SPEC = Path("src/data/pokemon/spaceworld_generated/spaceworld_species_info.h")
GFX_ROOT = Path("graphics/spaceworld/pokemon")

# folder-name overrides if needed (species token -> folder)
# token is WITHOUT trailing _SPACEWORLD, e.g. MR_MIME, HO_OH, etc.
FOLDER_OVERRIDES = {
    "MR_MIME": "mr__mime",
    # HO_OH usually maps cleanly to ho_oh
}

# Species-token aliases you identified (token -> token)
# token is WITHOUT trailing _SPACEWORLD.
ALIASES = {
    "BLOSSOMOLE": "PETAMOLE",
    "TANG": "TANGTRIP",
    "MEGANIUM": "BLOSSOMITE",
    "MEGANIUM": "BLOSSOMITE",
    # MR_MIME obvious, but sometimes your generator may have double underscores elsewhere
}

# Which file to use to detect "female variant exists"
FEMALE_SENTINEL = "anim_frontf.png"   # produced by your import script

# Use the gender macro that exists in pokeemerald-style codebases.
# (Your build error proved MON_MALE_FEMALE does NOT exist.)
GENDER_50_50 = "PERCENT_FEMALE(50)"


def token_from_species_macro(species_macro: str) -> str:
    # SPECIES_FOO_SPACEWORLD -> FOO
    m = re.match(r"SPECIES_([A-Z0-9_]+)_SPACEWORLD$", species_macro)
    if not m:
        return ""
    return m.group(1)


def folder_from_token(token: str) -> str:
    token = ALIASES.get(token, token)
    if token in FOLDER_OVERRIDES:
        return FOLDER_OVERRIDES[token]
    return token.lower()


def c_ident_from_folder(folder: str) -> str:
    # Must match your gen_spaceworld_pokemon_gfx.py naming rules:
    #   mr__mime -> MrMime
    #   ho_oh -> HoOh
    #   tangtrip -> Tangtrip
    #   mimejr -> Mimejr  (if your gfx generator emits Mimejr)
    parts = re.split(r"[_\-\s]+", folder.strip().lower())
    out = []
    for p in parts:
        if not p:
            continue
        # handle repeated underscores collapsing into empty parts automatically
        out.append(p[0].upper() + p[1:])
    return "".join(out)


def has_female_variant(folder: str) -> bool:
    # only gender mons that actually have the female-front asset
    return (GFX_ROOT / folder / FEMALE_SENTINEL).exists()


def patch_entry_body(body: str, ident: str, do_gender: bool) -> str:
    """
    body is inside { ... } including trailing commas/lines (but not the outer braces)
    ident is the Pascal-ish identifier used in gSwMonFrontPic_Ident etc.
    """

    # Always ensure the core sprite fields exist for Spaceworld
    # (These should already be present if your generator ran, but safe to enforce.)
    def ensure_field(b: str, field: str, value: str) -> str:
        # If field exists, replace its value; else insert near the top after speciesName/categoryName/types block.
        if re.search(rf"^\s*\.{re.escape(field)}\s*=", b, flags=re.M):
            return re.sub(rf"^(\s*\.{re.escape(field)}\s*=\s*).*(,)\s*$",
                          rf"\1{value}\2", b, flags=re.M)
        # insert after description/learnsets if possible, else after types, else after opening
        anchors = [
            r"^\s*\.evolutions\s*=",
            r"^\s*\.teachableLearnset\s*=",
            r"^\s*\.levelUpLearnset\s*=",
            r"^\s*\.description\s*=",
            r"^\s*\.types\s*=",
        ]
        for a in anchors:
            m = re.search(a, b, flags=re.M)
            if m:
                i = m.start()
                return b[:i] + f"    .{field} = {value},\n" + b[i:]
        return f"    .{field} = {value},\n" + b

    body = ensure_field(body, "frontPic",      f"gSwMonFrontPic_{ident}")
    body = ensure_field(body, "backPic",       f"gSwMonBackPic_{ident}")
    body = ensure_field(body, "palette",       f"gSwMonPalette_{ident}")
    body = ensure_field(body, "shinyPalette",  f"gSwMonShinyPalette_{ident}")

    # Female fields ONLY if the female asset exists
    if do_gender:
        body = ensure_field(body, "frontPicFemale", f"gSwMonFrontPic_{ident}F")
        body = ensure_field(body, "paletteFemale",  f"gSwMonPalette_{ident}")
        # optional: if you actually generated female shiny palettes and want them:
        # body = ensure_field(body, "shinyPaletteFemale", f"gSwMonShinyPalette_{ident}")

        # Set gender ratio (replace whatever is there) ONLY for these mons.
        if re.search(r"^\s*\.genderRatio\s*=", body, flags=re.M):
            body = re.sub(r"^(\s*\.genderRatio\s*=\s*).*(,)\s*$",
                          rf"\1{GENDER_50_50}\2", body, flags=re.M)
        else:
            # insert near other basic stats
            m = re.search(r"^\s*\.eggCycles\s*=", body, flags=re.M)
            if m:
                i = m.start()
                body = body[:i] + f"    .genderRatio = {GENDER_50_50},\n" + body[i:]
            else:
                body = f"    .genderRatio = {GENDER_50_50},\n" + body

    else:
        # If the file currently has female fields from a previous run, remove them.
        body = re.sub(r"^\s*\.frontPicFemale\s*=.*,\s*\n", "", body, flags=re.M)
        body = re.sub(r"^\s*\.backPicFemale\s*=.*,\s*\n", "", body, flags=re.M)
        body = re.sub(r"^\s*\.paletteFemale\s*=.*,\s*\n", "", body, flags=re.M)
        body = re.sub(r"^\s*\.shinyPaletteFemale\s*=.*,\s*\n", "", body, flags=re.M)
        body = re.sub(r"^\s*\.iconSpriteFemale\s*=.*,\s*\n", "", body, flags=re.M)
        body = re.sub(r"^\s*\.iconPalIndexFemale\s*=.*,\s*\n", "", body, flags=re.M)

        # And DO NOT touch genderRatio for these mons.

    return body


def main() -> int:
    if not SPEC.exists():
        print(f"ERROR: missing {SPEC}", file=sys.stderr)
        return 1
    if not GFX_ROOT.is_dir():
        print(f"ERROR: missing {GFX_ROOT} (did you run import_spaceworld_sprites.py?)", file=sys.stderr)
        return 1

    text = SPEC.read_text(encoding="utf-8")

    # Patch each entry: [SPECIES_XXX_SPACEWORLD] = { ... },
    entry_re = re.compile(
        r"(\[\s*(SPECIES_[A-Z0-9_]+_SPACEWORLD)\s*\]\s*=\s*\{\n)(.*?)(^\s*\},\s*$)",
        flags=re.M | re.S
    )

    patched = 0

    def repl(m: re.Match) -> str:
        nonlocal patched
        head = m.group(1)
        species_macro = m.group(2)
        body = m.group(3)
        tail = m.group(4)

        tok = token_from_species_macro(species_macro)
        if not tok:
            return m.group(0)

        folder = folder_from_token(tok)
        ident = c_ident_from_folder(folder)

        # Determine whether this mon actually has a female variant sprite asset.
        do_gender = has_female_variant(folder)

        new_body = patch_entry_body(body, ident, do_gender)
        if new_body != body:
            patched += 1
        return head + new_body + tail

    new_text = entry_re.sub(repl, text)

    if new_text != text:
        SPEC.write_text(new_text, encoding="utf-8")
    print(f"Patched entries: {patched}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
