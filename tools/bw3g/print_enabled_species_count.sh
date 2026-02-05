#!/usr/bin/env bash
set -euo pipefail
cd ~/decomps/pokeemerald-expansion_clean

cat > /tmp/print_enabled_species.c <<'C'
#include <stdio.h>
#include "global.h"
#include "constants/species.h"
#include "pokemon.h"

int main(void)
{
    int count = 0;
    int printed = 0;

    for (u16 s = 1; s <= NUM_SPECIES; s++)
    {
        if (IsSpeciesEnabled(s))
        {
            count++;
            if (printed < 50)
            {
                printf("ENABLED: %u\n", s);
                printed++;
            }
        }
    }

    printf("NUM_SPECIES=%u\n", (unsigned)NUM_SPECIES);
    printf("ENABLED_COUNT=%d\n", count);
    return 0;
}
C

# Build with the project includes so it sees IsSpeciesEnabled + NUM_SPECIES
gcc -I . -I include -Wno-unused-parameter -Wno-sign-compare /tmp/print_enabled_species.c -o /tmp/print_enabled_species

/tmp/print_enabled_species | tee enabled_species_count.out.txt
echo "WROTE enabled_species_count.out.txt"
