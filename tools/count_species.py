import re
from pathlib import Path

# Path to species definitions
species_path = Path("include/constants/species.h")

# Read all lines
lines = species_path.read_text().splitlines()

# Match lines that define a species ID
pattern = re.compile(r"#define\s+SPECIES_[A-Z0-9_]+\b")

# Filter matching species (excluding placeholders if needed)
species = [line for line in lines if pattern.search(line)]

# Show total
print(f"[✓] Total Pokémon species defined: {len(species)}")

# Optional: Uncomment below to list them
# for line in species:
#     print(line.strip())
