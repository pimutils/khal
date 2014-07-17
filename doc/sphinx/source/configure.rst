Configuring khal
================
khal reads configuration files in the *ini* syntax, meaning in understands
keys seperated from values by a **=**, while section and subsection names are
enclosed by single or double square brackets (like *[sectionname]* and
*[[subsectionname]]*.

Location of configuration file
------------------------------

Khal is looking for a configuration file named *khal.conf* in the following
places: in *$XDG_CONFIG_HOME/khal/* (on most systems this is *~/.config/khal/*
by default), *~/.khal/* and in the current directory. Alternatively you can
specifiy with configuration file to use with :option:`-c path/to/config` at
runtime.

copy ``khal.conf.sample`` to ``~/.khal/khal.conf`` or
``~/.config/khal/khal.conf`` and edit to your liking.


Calendar Section
----------------
The only section you need to have in your configuration file is a *[calendars]*
section with at least one subsection, with a configured *path*. Here is a small
example:

.. literalinclude:: ../../../tests/configs/small.conf
        :language: ini

syncing
-------

To get *khal* working with CalDAV you will first need to setup vdirsyncer_.
After each start *khal* will automatically check if anything has changed and
automatically update its caching db (this may take some time after the initial
sync, especially for large calendar collections). Therefore you might want to
execute *khal* automatically after syncing with vdirsyncer (e.g. via cron).

.. _vdirsyncer: https://github.com/untitaker/vdirsyncer


