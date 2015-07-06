Configuring
===========
:command:`khal` reads configuration files in the *ini* syntax, meaning it understands
keys separated from values by a **=**, while section and subsection names are
enclosed by single or double square brackets (like **[sectionname]** and
**[[subsectionname]]**).

Location of configuration file
------------------------------
:command:`khal` is looking for a configuration file named *khal.conf* in the
following places: in :file:`$XDG_CONFIG_HOME/khal/` (on most systems this is
:file:`~/.config/khal/` by default), :file:`~/.khal/` and in the current directory.
Alternatively you can specify with configuration file to use with :option:`-c
path/to/config` at runtime.

.. include:: configspec.rst

A minimal sample configuration could look like this:

Example
-------
.. literalinclude:: ../../tests/configs/simple.conf
  :language: ini

syncing
-------
To get :command:`khal` working with CalDAV you will first need to setup
vdirsyncer_.  After each start :command:`khal` will automatically check if
anything has changed and automatically update its caching db (this may take some
time after the initial sync, especially for large calendar collections).
Therefore you might want to execute :command:`khal` automatically after syncing
with :command:`vdirsyncer` (e.g. via :command:`cron`).

.. _vdirsyncer: https://github.com/untitaker/vdirsyncer


