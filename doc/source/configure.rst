Configuration
=============
:command:`khal` reads configuration files in the *ini* syntax, meaning it understands
keys separated from values by a **=**, while section and subsection names are
enclosed by single or double square brackets (like **[sectionname]** and
**[[subsectionname]]**). Any line beginning with a **#** will be treated as a
comment.

Help with initial configuration
-------------------------------
If you do not have a configuration file yet, running :command:`khal configure`
will launch a small, interactive tool that should help you with initial
configuration of :command:`khal`.

Location of configuration file
------------------------------
:command:`khal` is looking for configuration files in the following places and
order: :file:`$XDG_CONFIG_HOME/khal/config` (on most systems this is
:file:`~/.config/khal/config`), :file:`~/.khal/khal.conf` (deprecated) and a
file called :file:`khal.conf` in the current directory (deprecated).
Alternatively you can specify which configuration file to use with :option:`-c
path/to/config` at runtime.

.. include:: configspec.rst

A minimal sample configuration could look like this:

Example
-------
.. literalinclude:: ../../tests/configs/simple.conf
  :language: ini

Exemplary discover usage
-------------------------
If you have the following directory layout::

  ~/calendars
  ├- work/
  ├- home/
  └─ family/

where `work`, `home` and `family` are all different vdirs, each containing one
calendar, a matching calendar section could look like this:

.. highlight:: ini

::

  [[calendars]]
  path = ~/calendars/*
  type = discover
  color = dark green


Syncing
-------
To get :command:`khal` working with CalDAV you will first need to setup
vdirsyncer_.  After each start :command:`khal` will automatically check if
anything has changed and automatically update its caching db (this may take some
time after the initial sync, especially for large calendar collections).
Therefore, you might want to execute :command:`khal` automatically after syncing
with :command:`vdirsyncer` (e.g. via :command:`cron`).

.. _vdirsyncer: https://github.com/pimutils/vdirsyncer
