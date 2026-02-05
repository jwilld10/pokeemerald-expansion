#include <stdio.h>
#include "include/constants/species.h"

// One of these will exist depending on your branch/config.
// We'll probe by printing if they compile.
int main(void)
{
#ifdef FORM_SPECIES_START
    printf("FORM_SPECIES_START = %d\n", FORM_SPECIES_START);
#endif

#ifdef SPECIES_FOM_START
    printf("SPECIES_FOM_START = %d\n", SPECIES_FOM_START);
#endif

#ifdef SPECIES_FORM_START
    printf("SPECIES_FORM_START = %d\n", SPECIES_FORM_START);
#endif

#ifdef SPECIES_EXPANDED_FORMS_START
    printf("SPECIES_EXPANDED_FORMS_START = %d\n", SPECIES_EXPANDED_FORMS_START);
#endif

    printf("SPECIES_GENESECT_BW3G = %d\n", SPECIES_GENESECT_BW3G);
    printf("SPECIES_SKARMORY_BW3G = %d\n", SPECIES_SKARMORY_BW3G);

#ifdef FORM_SPECIES_START
    printf("GENESECT_BW3G - FORM_SPECIES_START = %d\n", SPECIES_GENESECT_BW3G - FORM_SPECIES_START);
#endif

    return 0;
}
