#include <stdio.h>
#include <stdint.h>
#include <inttypes.h>

int main(int argc, char **argv)
{
    if (argc != 2)
        return 2;
    FILE *input = fopen(argv[1], "rb");
    if (!input)
        return 1;
    uint32_t hash = UINT32_C(2166136261);
    int byte;
    while ((byte = fgetc(input)) != EOF)
        hash = (hash ^ (uint32_t)byte) * UINT32_C(16777619);
    int failed = ferror(input);
    if (fclose(input) || failed)
        return 1;
    printf("%08" PRIx32 "\n", hash);
    return 0;
}
