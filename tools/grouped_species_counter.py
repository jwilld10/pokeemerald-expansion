import re
from pathlib import Path
from collections import defaultdict

# === Configuration ===
GEN_PREFIXES = {
    1: "GEN_1_", 2: "GEN_2_", 3: "GEN_3_",
    4: "GEN_4_", 5: "GEN_5_"
}
CROSS_GEN_EVOS = {
    "SPECIES_SYLVEON", "SPECIES_OBSTAGOON", "SPECIES_PERRSERKER", "SPECIES_SIRFETCHD",
    "SPECIES_RUNERIGUS", "SPECIES_CURSOLA", "SPECIES_MR_RIME", "SPECIES_WEAVILE",
    "SPECIES_ROSERADE", "SPECIES_TOGEKISS", "SPECIES_HONCHKROW", "SPECIES_MISMAGIUS",
    "SPECIES_GALLADE", "SPECIES_FROSLASS", "SPECIES_MAGNEZONE", "SPECIES_LICKILICKY",
    "SPECIES_GLISCOR", "SPECIES_TANGROWTH", "SPECIES_RHYPERIOR", "SPECIES_DUSKNOIR",
    "SPECIES_YANMEGA", "SPECIES_ELECTIVIRE", "SPECIES_MAGMORTAR", "SPECIES_LEAFEON",
    "SPECIES_GLACEON"
}
REGIONAL_SUFFIXES = ("_ALOLAN", "_GALARIAN", "_HISUIAN", "_PALDEAN")

SPACEWORLD_PREFIXES = {
    "CHIX", "BELMITT", "BELRUN", "BALLERINE", "AQUALLO", "AQUARIUS", "ANCHORAGE", "BOMSHEAL"
}
BW3G_PATTERNS = ("_BW3", "_BW3G", "BW3G_", "BW3_", "_B3", "BW3", "GENESIS_MON_BW3G")

# === Read species list ===
species_path = Path("include/constants/species.h")
lines = species_path.read_text().splitlines()

pattern = re.compile(r"#define\s+(SPECIES_[A-Z0-9_]+)")
grouped = defaultdict(list)

for line in lines:
    match = pattern.search(line)
    if not match:
        continue
    mon = match.group(1)

    if any(mon.endswith(suffix) for suffix in REGIONAL_SUFFIXES):
        grouped["Regional Variants"].append(mon)
    elif mon in CROSS_GEN_EVOS:
        grouped["Cross-gen Evolutions"].append(mon)
    elif any(mon.startswith(f"SPECIES_{p}_") or mon == f"SPECIES_{p}" for p in SPACEWORLD_PREFIXES):
        grouped["Spaceworld"].append(mon)
    elif any(pat in mon for pat in BW3G_PATTERNS):
        grouped["BW3G"].append(mon)
    else:
        found_gen = False
        for gen, prefix in GEN_PREFIXES.items():
            if prefix in line:
                grouped[f"Gen {gen}"].append(mon)
                found_gen = True
                break
        if not found_gen:
            grouped["Other/Unknown"].append(mon)

# === Output summary ===
total = sum(len(lst) for lst in grouped.values())
print(f"[✓] Total Pokémon species defined: {total}\n")

for category, mons in sorted(grouped.items()):
    print(f"{category}: {len(mons)}")
