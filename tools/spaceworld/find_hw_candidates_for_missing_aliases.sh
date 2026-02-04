#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:?usage: $0 /path/to/repo}"
ROOT="$(realpath "$ROOT")"

echo "ROOT: $ROOT"
echo

python3 - "$ROOT" <<'PY'
import re, sys
from pathlib import Path

root = Path(sys.argv[1])

# The SPACEWORLD species still missing in pokeemerald-expansion after your imports.
missing_spaceworld = [
  "BELLRUN","BELMITT","BOMSHEAL","CORASUN","CRUIZE","ELEBABE","GELANIA","GUPGOLD","KURSTRAW","METTO",
  "NYANYA","PANGSHI","PARAMITE","PETAMOLE","PETICORN","PRAXE","PUDDIPUP","TANGTRIP","TRIPSTAR"
]

# Alias map: SPACEWORLD name -> list of possible names in source repos (Gold97SGB, etc).
# Fill in as you discover them. Start with the ones you already know.
ALIASES = {
  "TANGTRIP": ["BURGELA"],
  "NYANYA": ["COINPUR"],
  # Likely punctuation variants:
  "MR_MIME": ["MRMIME", "MR. MIME", "MR_MIME"],
  "FARFETCH_D": ["FARFETCHD", "FARFETCH'D", "FARFETCH_D"],
}

# Some repos write things like "DexEntry:" labels, others use DEX_ constants.
# We'll just search broadly in .asm/.inc and then look nearby for HW encodings.

pair_dw = re.compile(r'^\s*dw\s+(\d+)\s*,\s*(\d+)\b', re.I)          # dw 200, 179
db_height = re.compile(r'^\s*db\s+(\d+)\b', re.I)                   # db 7
dw_weight = re.compile(r'^\s*dw\s+(\d+)\b', re.I)                   # dw 69

# Also handle "db DEX_FOO" style lines in base_stats/*.inc, which might not include hw at all,
# but can tell us the canonical token used in that repo.
dex_const = re.compile(r'\bDEX[_ ]+([A-Z0-9_]+)\b')

def normalize_token(tok: str) -> str:
    return re.sub(r'[^A-Z0-9_]+', '', tok.upper())

def token_variants(space_name: str):
    base = normalize_token(space_name)
    vars = {base}

    # include alias list if present
    for a in ALIASES.get(base, []):
        vars.add(normalize_token(a))

    # heuristic: remove underscores (FARFETCH_D -> FARFETCHD)
    vars.add(base.replace("_",""))

    # heuristic: if ends with _F/_M (NIDORAN_F), also try NIDORANF
    if base.endswith("_F") or base.endswith("_M"):
        vars.add(base.replace("_",""))

    # heuristic: Mr Mime variants already covered by punctuation stripping
    return sorted(vars)

def scan_file(path: Path, tokens):
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return None

    token_res = [re.compile(r'\b' + re.escape(t) + r'\b', re.I) for t in tokens]

    # Find any line that mentions one of our tokens, then search ±N for hw patterns.
    for i, line in enumerate(lines):
        if not any(r.search(line) for r in token_res):
            continue

        start = max(0, i - 40)
        end = min(len(lines), i + 80)
        window = lines[start:end]

        # pattern 1: dw H, W (Gold97 style includes do this)
        for j, wline in enumerate(window):
            m = pair_dw.match(wline)
            if m:
                return (path, start + j + 1, f"dw {m.group(1)}, {m.group(2)}")

        # pattern 2: db H then shortly after dw W (pokegold-spaceworld style)
        for j, wline in enumerate(window):
            mh = db_height.match(wline)
            if not mh:
                continue
            h = mh.group(1)
            for k in range(j + 1, min(j + 10, len(window))):
                mw = dw_weight.match(window[k])
                if mw:
                    return (path, start + j + 1, f"db {h} -> dw {mw.group(1)}")

        # If we found a mention but not HW, still useful: show DEX_ const if present in window
        for wline in window:
            m = dex_const.search(wline.upper())
            if m:
                return (path, i + 1, f"(mention) has DEX_{m.group(1)} nearby but no hw pattern found")

    return None

files = list(root.rglob("*.asm")) + list(root.rglob("*.inc"))
print(f"Scanning {len(files)} files...\n")

for sp in missing_spaceworld:
    toks = token_variants(sp)
    hit = None
    for f in files:
        hit = scan_file(f, toks)
        if hit:
            break

    print(f"== {sp} ==")
    print(f"  tokens tried: {', '.join(toks)}")
    if hit:
        p, line, desc = hit
        print(f"  HIT: {p}:{line}  {desc}")
    else:
        print("  (no candidates found)")
    print()

PY
