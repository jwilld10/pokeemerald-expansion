import re
from pathlib import Path

# === Config ===
species_file = Path("species_dump.txt")  # Dump of all species in the ROM
dex_texts_dir = Path("tools/bw3g/text")  # Where the .asm dex files are
missing = []

# === Load species dump
all_species = species_file.read_text().splitlines()

# === Filter BW3G and Spaceworld species
spaceworld_species = [s for s in all_species if s.endswith("_BW3G") and not s.endswith("GENESIS_MON_BW3G")]

# === Check for corresponding dex text files
for species in spaceworld_species:
    base = species.replace("SPECIES_", "").replace("_BW3G", "").lower()
    path = dex_texts_dir / f"{base}.asm"
    if not path.exists():
        missing.append((species, path))

# === Report
print(f"[✓] Total Spaceworld/BW3G species found: {len(spaceworld_species)}")
if missing:
    print(f"[✗] Missing Pokédex text for {len(missing)} species:")
    for sp, p in missing:
        print(f"    - {sp} → {p}")
else:
    print("[✓] All Spaceworld/BW3G species have Pokédex entries.")
