/* SPDX-License-Identifier: GPL-3.0-only */
#ifndef MAC_M8_START_H
#define MAC_M8_START_H
#include "m8_image.h"
#include "m8_heap.h"

enum { Mac8OutputLimit = 256, Mac8MaxBudget = 16777216 };

typedef struct Mac8Stop Mac8Stop;
struct Mac8Stop {
    unsigned long long pc, last_pc, arg0, arg1, arg2, arg3, link;
    unsigned int steps, name, locale_calls, alloc_calls;
    unsigned int exit_code, stdout_bytes, stderr_bytes, file_opens, file_reads;
    unsigned char stdout_data[Mac8OutputLimit], stderr_data[Mac8OutputLimit];
};

enum {
    Mac8InputLimit = 1024*1024, Mac8StackBytes = 65536, Mac8ServiceBytes = 4096, Mac8WritableBytes = 4096,
    Mac8ArenaBytes = Mac8Limit+Mac8StackBytes+Mac8ServiceBytes+Mac8HeapBytes+Mac8WritableBytes
};

/* Start the pinned --version profile. A nonzero guest stack guard enables
 * C-locale service and its read-only guest data page. An unresolved import
 * returns 1, guest exit returns 2, and a guest fault or budget stop returns 0.
 * The caller supplies separate immutable image, arena and receipt storage. */
int mac8_start(const unsigned char *, unsigned int, unsigned char *,
               unsigned int, unsigned long long, Mac8Stop *);

/* The optional immutable input is exposed only as guest input.json. */
int mac8_run(const unsigned char *, unsigned int, unsigned char *, unsigned int,
             unsigned long long, unsigned int, const char *const *, unsigned int, const unsigned char *, unsigned int, Mac8Stop *);
/* M9 accepts one immutable input under a caller-selected guest basename.
 * The name, bytes and argv remain valid for the duration of the run. */
int mac9_grant_name(const char *);
/* An optional rollback journal belongs to the same exclusive database grant.
 * The caller must refuse a grant with a pre-existing journal until recovery is supported.
 * Open and remove accept the already-pinned database descriptor as context. */
typedef struct Mac9Journal Mac9Journal;
struct Mac9Journal {
    int (*open)(int, int);
    int (*close)(int);
    int (*remove)(int);
    int (*sync)(int);
};
typedef struct Mac9Database Mac9Database;
struct Mac9Database {
    const char *name;
    int fd, exclusive;
    long (*size)(int);
    long (*read_at)(int, void *, unsigned int, unsigned long);
    long (*write_at)(int, const void *, unsigned int, unsigned long);
    const Mac9Journal *journal;
};
int mac9_run_database(const unsigned char *, unsigned int, unsigned char *, unsigned int,
             unsigned long long, unsigned int, const char *const *, unsigned int,
             const char *, const unsigned char *, unsigned int, Mac9Database *, Mac8Stop *);
int mac9_run(const unsigned char *, unsigned int, unsigned char *, unsigned int,
             unsigned long long, unsigned int, const char *const *, unsigned int,
             const char *, const unsigned char *, unsigned int, Mac8Stop *);
#endif
