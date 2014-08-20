Configuring khal
================
khal reads configuration files in the *ini* syntax, meaning in understands
keys separated from values by a **=**, while section and subsection names are
enclosed by single or double square brackets (like *[sectionname]* and
*[[subsectionname]]*.

Location of configuration file
------------------------------
Khal is looking for a configuration file named *khal.conf* in the following
places: in *$XDG_CONFIG_HOME/khal/* (on most systems this is *~/.config/khal/*
by default), *~/.khal/* and in the current directory. Alternatively you can
specifiy with configuration file to use with :option:`-c path/to/config` at
runtime.

.. include:: configspec.rst

A minimal sample configuration could look like this:

Example
-------
.. literalinclude:: ../../tests/configs/simple.conf
  :language: ini

syncing
-------
To get *khal* working with CalDAV you will first need to setup vdirsyncer_.
After each start *khal* will automatically check if anything has changed and
automatically update its caching db (this may take some time after the initial
sync, especially for large calendar collections). Therefore you might want to
execute *khal* automatically after syncing with vdirsyncer (e.g. via cron).

.. _vdirsyncer: https://github.com/untitaker/vdirsyncer


