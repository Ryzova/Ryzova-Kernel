/* Phase 5C source compatibility for narrow, relative POSIX-style paths. */
#ifndef RYZ_WIN32_SOURCE_WINDOWS_H
#define RYZ_WIN32_SOURCE_WINDOWS_H
#include <sys/stat.h>
#include <unistd.h>
#include <stddef.h>

static inline int CreateDirectoryA(const char *path, const void *security)
{
    return path && !security && mkdir(path, 0777) == 0;
}

static inline int RemoveDirectoryA(const char *path)
{
    return path && rmdir(path) == 0;
}
#endif
