Changelog
#########
All notable changes to this project should be documented here.
For more detailed information have a look at the git log.

Package maintainers and users who have to manually update their installation
may want to subscribe to `GitHub's tag feed
<https://github.com/geier/khal/tags.atom>`_.

0.7.1
======
released 2016-10-11

This is a backport of an important bugfix to the last version of khal that still
supports python 2.7.

* **IMPORTANT BUGFIX** fixed a bug that lead to imported events being
  erroneously shifted if they had a timezone identifier that wasn't an Olson
  database identifier. All users are advised to upgrade as soon as possible. To
  see if you are affected by this and how to resolve any issues, please see the
  release announcement (khal/doc/source/news/khal084.rst or
  http://lostpackets.de/khal/news/khal084.html). Thanks to Wayne Werner for
  finding and reporting this bug.


0.7.0
=====
released on 2015-11-24

There are no new or dropped dependencies.

* most of the internal representation of events was rewritten, the current
  benefit is that floating events are properly represented now, hopefully more
  is to come (Christian Geier)
* `printformats` uses a more sensible date now (John Shea)
* khal and ikhal can now highlight dates with events, at the moment, enabling it
  does noticably slow down (i)khal's start; set *[default] highlight_event_days
  = True* and see section *[highlight_days]* for further configuration (Dominik
  Joe Pantůček)
* fixed line wrapping for `at` (Thomas Schape)
* `calendar` and `agenda` optionally print location and description of all
  events, enable with the new --full/-f flag (Thomas Schaper)
* updated and improved zsh completion file (Oliver Kiddle)
* FIX: deleting events did not always work if an event with the same filename existed
  in an other calendar (but no data lost incurred) (Christian Geier)

ikhal
-----
* events are now displayed nicer (Thomas Glanzmann)
* support for colorschemes, a *light* and *dark* one are currently included,
  help is wanted to make them prettier and more functional (config option
  *[view] theme: (dark|light)*) (Christian Geier)
* ikhal can now display frames around some user interface elements, making it
  nicer to look at in some eyes (config option *[view] frame: True*) (Christian
  Geier)
* events can now be duplicated (default keybinding: *p*) (Christian Geier)
* events created while time ranges are selected (default keybinding to enable date range
  selection: *v*) will default to that date range (Christian Geier)
* when trying to delete recurring events, users are now asked if they want to
  delete the complete event or just this instance (Christian Geier)

0.6.0
=====
2015-07-15

* BUGFIX Recurrent events with a THISANDFUTURE parameter could affect other
  events. This could lead to events not being found by the normal lookup
  functionality when they should and being found when they shouldn't. As the
  second case should result in an error that nobody reported yet, I hope nobody
  got bitten by this.
* new dependency for running the tests: freezegun
* new dependency for setup from scm: setuptools_scm
* khal now needs to be installed for building the documentation

* ikhal's should now support ctrl-e, ctrl-a, ctrl-k and ctrl-u in editable text
  fields (Thomas Glanzmann)
* ikhal: space and backspace are new (additional) default keybindings for right
  and left (Pierre David)
* when editing descriptions you can now insert new lines (Thomas Glanzmann)
* khal should not choose an arbitrary default calendar anymore (Markus
  Unterwaditzer)
* the zsh completion file has been updated (Hugo Osvaldo Barrera)
* new command `import` lets users import .ics files (Christian Geier)
* khal should accept relative dates on the command line (today, tomorrow and
  weekday names) (Christian Geier)
* keybinding for saving an event from ikhal's event editor (default is `meta +
  enter`) (Christian Geier)


0.5.0
=====
released on 2015-06-01

* fixed several bugs relating to events with unknown timezones but UNTIL, RDATE
  or EXDATE properties that are in Zulu time (thanks to Michele Baldessari for
  reporting those)
* bugfix: on systems with a local time of UTC-X dealing with allday events lead
  to crashes
* bugfix: British summer time is recognized as daylight saving time (Bradley
  Jones)
* compatibility with vdirsyncer 0.5

* new command `search` allows to search for events
* user changeable keybindings in ikhal, with hjkl as default alternatives for
  arrows in calendar browser, see documentation for more details
* new command `at` shows all events scheduled for a specific datetime
* support for reading birthdays from vcard collections (set calendar/collection
  `type` to *birthdays*)
* new command `printformats` prints a fixed date in all configured date-time
  settings
* `new` now supports the `--until`/`-u` flag to specify until when recurring
  events should run (Micah Nordland)
* python 3 (>= 3.3) support (Hugo Osvaldo Barrera)

ikhal
-----
* minimal support for reccurring events in ikhal's editor (Micah Nordland)
* configurable view size in ikhal (Bradley Jones)
* show events organizers (Bradley Jones)
* major reorganisation of ikhal layout (Markus Unterwaditzer)

0.4.0
=====
released on 2015-02-02

dependency changes
------------------
* new dependency: click>3.2
* removed dependency: docopt
* note to package mantainers: `requirements.txt` has been removed, dependencies
  are still listed in `setup.py`

note to users
-------------
* users will need to delete the local database, no data should be lost (and
  khal will inform the user about this)

new and changed features
------------------------
* new config_option: `[default] print_new`, lets the user decide what should be
  printed after adding a new event
* new config option: `[default] show_all_days` lets users decide if they want to
  see days without any events in agenda and calendar view (thanks to Pierre
  David)
* khal (and ikhal) can now display weeknumbers
* khal new can now create repetitive events (with --repeat), see documentation
  (thanks to Eric Scheibler)
* config file: the debug option has been removed (use `khal -v` instead)
* FIX: vtimezones were not assembled properly, this lead to spurious offsets of
  events in some other calendar applications
* change in behaviour: recurring events are now always expanded until 2037
* major speedup in inserting events into the caching database, especially
  noticeable when running khal for the first time or after an deleting the
  database (Thanks to Markus Unterwaditzer)
* better support for broken events, e.g. events ending before they start
  (Thanks to Markus Unterwaditzer)
* more recurrence rules are supported, khal will print warnings on unsupported
  rules

ikhal
-----
* ikhal's calendar should now be filled on startup
* pressing `t` refocuses on today
* pressing ctrl-w in input fields should delete the last word before the cursor
* when the focus is set on the events list/editor, the current date should
  still be visible in the calendar

0.3.1
=====
released on 2014-09-08

* FIX: events deleted in the vdir are not shown anymore in khal. You might want
  to delete your local database file, if you have deleted any events on the
  server.
* FIX: in some cases non-ascii characters were printed even if unicode_symbols
  is set to False in the config
* FIX: events with different start and end timezones are now properly exported
  (the end timezone was disregarded when building an icalendar, but since
  timezones cannot be edited anyway, this shouldn't have caused any problems)
* FIX: calendars marked as read-only in the configuration file should now really
  be read-only

0.3.0
=====
released on 2014-09-03

* new unified documentation
    * html documentation (website) and man pages are all generated from the same
      sources via sphinx (type `make html` or `make man` in doc/, the result
      will be build in *build/html* or *build/man* respectively
    * the new documentation lives in doc/
    * the package sphinxcontrib-newsfeed is needed for generating the html
      version (for generating an RSS feed)
    * the man pages live doc/build/man/, they can be build by running
      `make man` in doc/sphinx/
* new dependencies: configobj, tzlocal>=1.0
* **IMPORTANT**: the configuration file's syntax changed (again), have a look at the new
  documentation for details
* local_timezone and default_timezone will now be set to the timezone the
  computer is set to (if they are not set in the configuration file)
