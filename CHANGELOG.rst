Changelog
#########
All notable changes to this project should be documented here.
For more detailed information have a look at the git log.

Package maintainers and users who have to manually update their installation
may want to subscribe to `GitHub's tag feed
<https://github.com/geier/khal/tags.atom>`_.

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
