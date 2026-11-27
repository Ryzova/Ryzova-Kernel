/* SPDX-License-Identifier: GPL-3.0-only */
int mac_grant_init(char *);
int mac_grant_open_database(const char *);
int mac_grant_open(const char *);
long mac_grant_read(int, void *, unsigned int, unsigned long);
long mac_grant_write(int, const void *, unsigned int, unsigned long);
void mac_grant_close(int);
long mac_grant_size(int);
#ifdef MAC_PLAN9
int mac_grant_init_journal_root(char *);
int mac_grant_journal_init(const char *, int);
int mac_grant_journal_open(int, int);
int mac_grant_journal_close(int);
int mac_grant_journal_remove(int);
int mac_grant_journal_sync(int);
#endif
