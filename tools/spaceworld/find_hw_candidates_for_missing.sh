#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:?usage: $0 /path/to/repo}"
ROOT="$(realpath "$ROOT")"

missing=(
  BELLRUN BELMITT BOMSHEAL CORASUN CRUIZE ELEBABE GELANIA GUPGOLD KURSTRAW METTO
  NYANYA PANGSHI PARAMITE PETAMOLE PETICORN PRAXE PUDDIPUP TANGTRIP TRIPSTAR
)

echo "ROOT: $ROOT"
echo

python3 - "$ROOT" <<'PY'
import re
import sys
from pathlib import Path

root = Path(sys.argv[1])

missing = [
  "BELLRUN","BELMITT","BOMSHEAL","CORASUN","CRUIZE","ELEBABE","GELANIA","GUPGOLD","KURSTRAW","METTO",
  "NYANYA","PANGSHI","PARAMITE","PETAMOLE","PETICORN","PRAXE","PUDDIPUP","TANGTRIP","TRIPSTAR"
]

pair_dw = re.compile(r'^\s*dw\s+(\d+)\s*,\s*(\d+)', re.I)
db_height = re.compile(r'^\s*db\s+(\d+)', re.I)
dw_weight = re.compile(r'^\s*dw\s+(\d+)', re.I)

def scan_file(path, token):
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return []

    hits = []
    token_re = re.compile(token, re.I)

    for i, line in enumerate(lines):
        if not token_re.search(line):
            continue

        start = max(0, i - 30)
        end = min(len(lines), i + 60)
        window = lines[start:end]

        # pattern: dw 200, 179
        for j, wline in enumerate(window):
            m = pair_dw.match(wline)
            if m:
                hits.append((path, start + j + 1, f"dw {m.group(1)}, {m.group(2)}"))
                return hits

        # pattern: db 7  -> dw 69
        for j, wline in enumerate(window):
            mh = db_height.match(wline)
            if not mh:
                continue
            h = mh.group(1)
            for k in range(j + 1, min(j + 8, len(window))):
                mw = dw_weight.match(window[k])
                if mw:
                    hits.append((path, start + j + 1, f"db {h} -> dw {mw.group(1)}"))
                    return hits

    return hits

files = list(root.rglob("*.asm")) + list(root.rglob("*.inc"))
print(f"Scanning {len(files)} files...")

for token in missing:
    found = []
    for f in files:
        r = scan_file(f, token)
        if r:
            found.extend(r)

    print(f"\n== {token} ==")
    if found:
        for p, line, txt in found[:6]:
            print(f"{p}:{line}  {txt}")
    else:
        print("(no hw candidates found)")

PY
