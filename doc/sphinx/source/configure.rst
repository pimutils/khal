Configuring khal
================

copy ``khal.conf.sample`` to ``~/.khal/khal.conf`` or
``~/.config/khal/khal.conf`` and edit to your liking.

syncing
-------

To get *khal* working with CalDAV you will first need to setup vdirsyncer_.
After each start *khal* will automatically check if anything has changed and
automatically update its caching db (this may take some time after the initial
sync, especially for large calendar collections). Therefore you might want to
execute *khal* automatically after syncing with vdirsyncer (e.g. via cron).

.. _vdirsyncer: https://github.com/untitaker/vdirsyncer


