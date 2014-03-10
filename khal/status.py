
OK = 0  # not touched since last sync
NEW = 1  # new card, needs to be created on the server
CHANGED = 2  # properties edited or added (news to be pushed to server)
NEWNOTSAVED = 3  # new and not event saved to disk/db yet
CALCHANGED = 8  # copied to another account, should be deleted in this account
DELETED = 9  # marked for deletion (needs to be deleted on server)
NEWDELETE = 11  # card should be deleted on exit (not yet on the server)
