import re
from pathlib import Path

# === Configuration ===
species_hdr = Path("include/constants/species.h")
dex_dir = Path("tools/bw3g/text")
spaceworld_prefixes = {"ANCHORAGE", "AQUALLO", "AQUARIUS", "BALLERINE", "BELMITT", "BELRUN", "CHIX"}

# === Extract Spaceworld Species ===
species_lines = species_hdr.read_text(encoding="utf-8", errors="replace").splitlines()
spaceworld_species = []

for line in species_lines:
    m = re.search(r'#define\s+(SPECIES_([A-Z0-9_]+))\b', line)
    if not m:
        continue
    species_token, species_name = m.group(1), m.group(2)
    prefix = species_name.split("_")[0]
    if prefix in spaceworld_prefixes:
        spaceworld_species.append((species_token, species_name.lower()))

# === Check for Dex Entries ===
missing = []
for token, name in spaceworld_species:
    dex_path = dex_dir / f"{name}.asm"
    if not dex_path.exists():
        missing.append((token, str(dex_path)))

# === Report ===
print(f"[✓] Found {len(spaceworld_species)} Spaceworld species.")
if missing:
    print(f"[✗] Missing dex entries for {len(missing)} species:")
    for tok, path in missing:
        print(f"    - {tok} → {path}")
else:
    print("[✓] All Spaceworld species have corresponding dex entry files.")
