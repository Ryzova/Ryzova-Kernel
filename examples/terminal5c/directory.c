#include <windows.h>
#include <stdio.h>
#include <string.h>

int main(void)
{
    const char *directory = "phase5c-work";
    const char *path = "phase5c-work/data";
    const char message[] = "Ryzova";
    char result[sizeof message];
    if (!CreateDirectoryA(directory, NULL))
        return 1;
    if (CreateDirectoryA(directory, NULL))
        return 2;
    FILE *file = fopen(path, "wb");
    if (!file || fwrite(message, 1, sizeof message, file) != sizeof message || fclose(file))
        return 3;
    if (RemoveDirectoryA(directory))
        return 4;
    file = fopen(path, "rb");
    if (!file || fread(result, 1, sizeof result, file) != sizeof result || fclose(file))
        return 5;
    if (memcmp(message, result, sizeof result) || remove(path) || !RemoveDirectoryA(directory))
        return 6;
    return 0;
}
