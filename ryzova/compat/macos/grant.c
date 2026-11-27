/* SPDX-License-Identifier: GPL-3.0-only */
#ifdef MAC_PLAN9
#include <u.h>
#include <libc.h>
#ifdef MAC_SQLITE_JOURNAL
#include "../windows/sync_protocol.h"
#endif
#else
#define _GNU_SOURCE
#include <fcntl.h>
#include <linux/openat2.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <unistd.h>
#endif
#include "grant.h"

enum { MaxFile = 65536, MaxName = 63 };

#ifdef MAC_PLAN9
/* The bind pins the selected directory in this launcher's private namespace. */
static Dir *root_identity;
#else
static int rootfd = -1;
#endif

#ifdef MAC_PLAN9
static int
pin_root(char *path, int flags)
{
    if(rfork(RFNAMEG)<0 || bind(path, "/mnt", flags)<0)
        return 0;
    root_identity = dirstat("/mnt");
    return root_identity!=nil && (root_identity->mode&DMDIR)!=0;
}

#ifdef MAC_SQLITE_JOURNAL
int
mac_grant_init_journal_root(char *path)
{
    return pin_root(path, MREPL|MCREATE);
}
#endif
#endif

int
mac_grant_init(char *path)
{
#ifdef MAC_PLAN9
    return pin_root(path, MREPL);
#else
    rootfd = open(path, O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
    return rootfd>=0;
#endif
}

static int
valid_name(const char *name)
{
    unsigned int i;
    unsigned char c;

    /* Single ASCII basename. The first byte cannot start a dot component. */
    for(i=0; i<=MaxName && name[i]; i++){
        c = name[i];
        if((c>='a' && c<='z') || (c>='A' && c<='Z') || (c>='0' && c<='9'))
            continue;
        if(i==0 || (c!='.' && c!='_' && c!='-'))
            return 0;
    }
    return i>0 && i<=MaxName;
}

#ifdef MAC_PLAN9
static int
ordinary(Dir *file, int exclusive)
{
    return file!=nil && file->qid.type==(exclusive ? QTEXCL : 0) &&
           (file->mode&~0777UL)==(exclusive ? DMEXCL : 0) &&
           file->type==root_identity->type && file->dev==root_identity->dev &&
           file->length>=0 && file->length<=MaxFile;
}
#endif

static int
grant_open(const char *name, int exclusive)
{
    int fd;
#ifdef MAC_PLAN9
    Dir *before, *after;
    char path[sizeof "/mnt/" + MaxName];

    if(root_identity==nil || !valid_name(name))
        return -1;
    snprint(path, sizeof path, "/mnt/%s", name);
    before = dirstat(path);
    if(!ordinary(before, exclusive)){
        free(before);
        return -1;
    }
    fd = open(path, ORDWR);
    if(fd>=0){
        after = dirfstat(fd);
        if(!ordinary(after, exclusive) || after->qid.path!=before->qid.path){
            close(fd);
            fd = -1;
        }
        free(after);
    }
    free(before);
#else
    struct flock lock = { .l_type = F_WRLCK, .l_whence = SEEK_SET };
    struct open_how how = {
        .flags = O_RDWR|O_NONBLOCK|O_CLOEXEC,
        .resolve = RESOLVE_BENEATH|RESOLVE_NO_SYMLINKS|RESOLVE_NO_XDEV
    };
    struct stat file;

    if(rootfd<0 || !valid_name(name))
        return -1;
    fd = syscall(SYS_openat2, rootfd, name, &how, sizeof how);
    if(fd>=0 && (fstat(fd, &file)<0 || !S_ISREG(file.st_mode) ||
                 file.st_nlink!=1 || file.st_size<0 || file.st_size>MaxFile ||
                 (exclusive && fcntl(fd, F_OFD_SETLK, &lock)<0))){
        close(fd);
        fd = -1;
    }
#endif
    return fd;
}

int
mac_grant_open(const char *name)
{
    return grant_open(name, 0);
}

int
mac_grant_open_database(const char *name)
{
    /* Require single-opener storage on Plan 9; hold a whole-file OFD lock on Linux. */
    return grant_open(name, 1);
}

long
mac_grant_size(int fd)
{
#ifdef MAC_PLAN9
    Dir *file = dirfstat(fd);
    long size = ordinary(file, 1) || ordinary(file, 0) ? (long)file->length : -1;
    free(file);
    return size;
#else
    struct stat file;
    if(fstat(fd, &file)<0 || file.st_size<0 || file.st_size>MaxFile)
        return -1;
    return (long)file.st_size;
#endif
}

long
mac_grant_read(int fd, void *data, unsigned int size, unsigned long offset)
{
    if(offset>MaxFile || size>MaxFile-offset)
        return -1;
    return pread(fd, data, size, offset);
}

long
mac_grant_write(int fd, const void *data, unsigned int size, unsigned long offset)
{
    if(offset>MaxFile || size>MaxFile-offset)
        return -1;
    return pwrite(fd, data, size, offset);
}

void
mac_grant_close(int fd)
{
    close(fd);
}

#ifdef MAC_SQLITE_JOURNAL
static int barrier = -1, journal_failed;
static CwSyncNonce nonce;
static char journal_path[sizeof "/mnt/" + MaxName];

int
mac_grant_journal_init(const char *name, int fd)
{
    Dir *cap, *existing;
    char banner[32], error[ERRMAX];
    int valid;

    if(!valid_name(name) || strlen(name)+sizeof "-journal"-1>MaxName)
        return 0;
    cap = dirfstat(fd);
    valid = cap!=nil && cap->type==root_identity->type && cap->dev==root_identity->dev &&
            cap->qid.type==0 && cap->qid.path==~(CwSyncNonce)1 && cap->qid.vers==1;
    free(cap);
    if(!valid || pread(fd, banner, sizeof banner, 0)!=13 ||
       memcmp(banner, "CWFS_SYNC_V1\n", 13))
        return 0;
    snprint(journal_path, sizeof journal_path, "/mnt/%s-journal", name);
    existing = dirstat(journal_path);
    if(existing){
        free(existing);
        werrstr("existing rollback journal requires recovery");
        return 0;
    }
    rerrstr(error, sizeof error);
    if(!strstr(error, "not exist") && !strstr(error, "not found"))
        return 0;
    barrier = fd;
    nonce = nsec();
    return 1;
}

int
mac_grant_journal_open(int database, int create_new)
{
    Dir *file;
    int fd;

    USED(database);
    if(barrier<0 || journal_failed || !create_new)
        return -1;
    fd = create(journal_path, ORDWR|OEXCL, 0600);
    if(fd<0){
        fprint(2, "create rollback journal %s: %r\n", journal_path);
        return -1;
    }
    file = dirfstat(fd);
    if(!ordinary(file, 0)){
        if(file)
            fprint(2, "journal metadata type=%ud dev=%ud qid=%ux mode=%lux size=%lld (root %ud/%ud)\n",
                   file->type, file->dev, file->qid.type, file->mode, file->length, root_identity->type, root_identity->dev);
        else
            fprint(2, "stat rollback journal: %r\n");
        close(fd);
        fd = -1;
    }
    free(file);
    return fd;
}

int
mac_grant_journal_close(int fd)
{
    if(close(fd)<0){
        journal_failed = 1;
        return -1;
    }
    return 0;
}

int
mac_grant_journal_sync(int fd)
{
    char request[22], reply[32];
    int count;

    USED(fd);
    if(barrier<0 || journal_failed || nonce==~(CwSyncNonce)0)
        return -1;
    cw_sync_request(++nonce, request);
    if(pwrite(barrier, request, sizeof request, 0)==sizeof request){
        count = pread(barrier, reply, sizeof reply, 0);
        if(count>=0 && cw_sync_ack(reply, count, nonce))
            return 0;
    }
    journal_failed = 1;
    return -1;
}

int
mac_grant_journal_remove(int database)
{
    if(journal_failed || remove(journal_path)<0)
        return -1;
    return mac_grant_journal_sync(database);
}
#endif
