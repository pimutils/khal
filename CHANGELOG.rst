Changelog
#########
All notable changes to this project should be documented here.
For more detailed information have a look at the git log.

Package maintainers and users who have to manually update their installation
may want to subscribe to `GitHub's tag feed
<https://github.com/geier/khal/tags.atom>`_.

0.12.0
======
2025-04-14

* FIX Don't install tests module.
* DROPPED support for python versions < 3.9.

0.11.4
======
2025-04-10

* UPDATED REQUIREMENT urwid is now required >= 2.6.15
* NEW REQUIREMENT for tests on python >= 3.12: pkg_resources
* optimization in ikhal when editing events in the far future or past
* FIX an issue in ikhal with updating the view of the event list after editing
  an event
* NEW properties of ikhal themes (dark and light) can now be overriden from the
  config file (via the new [palette] section, check the documenation)
* NEW timedelta strings can now have a leading ``+``, e.g. ``+1d``
* NEW Add ``--json`` option to output event data as JSON objects
* NEW Add default alarms configuration option
* FIX defaults for ``default_event_duration`` and ``default_dayevent_duration``
  where mixed up, ``default_dayevent_duration`` is the default for all-day events
* NEW event format option ``status-symbol`` which represents the status of an
  event with a symbol (e.g. ``✓`` for confirmed, ``✗`` for cancelled, ``?`` for
  tentative)
* NEW event format option ``partstat-symbol`` which represents the participation
  status of an event with a symbol (e.g. ``✓`` for accepted, ``✗`` for declined,
  ``?`` for tentative); partication status is shown for the email addresses
  configured for the event's calendar
* NEW support for color theme, command, and formatter plugins
* FIX an issue where ikhal would forget changes to time or date fields if you
  left the field with page up/down or meta+enter
* NEW support python 3.13
* CHANGE various UI improvments to ikhal.
* FIX Deleting multiple of instances of a recurring event in ikhal
* NEW Add ``enable_mouse`` configuration option.
* CHANGE the ``atomicwrites`` library is no longer required.

0.11.3
======
2024-02-12

* FIX support urwid 2.4.2

0.11.2
======
2023-06-07

* FIX khal `at` also uses `event_format` not `agenda_event_format`
* FIX duplicating an event using `p` in ikhal
* NEW Add ability to change the minimum number of months displayed with
  `min_calendar_display`
* FIX ikhal don't crash when jumping long distances in time
* FIX do not use urwid's private methods, would crash with latest urwid version
* FIX light colorscheme in ikhal, would crash with recent urwid versions
* FIX better error messages when we cannot import an event

0.11.1
======
2023-04-23

* FIX README.rst formatting to allow upload to PyPI

0.11.0
======
2023-04-23

* DROPPED support for python versions < 3.8
* UPDATED REQUIREMENT pytz is now required >= 2018.7
* NEW test REQUIREMENT: packaging
* FIX support in tests for pytz version numbers of the format year.month.minor
* FIX deleting of instances of recurring events in ikhal
* FIX if a `discover` collection is set to "readonly", discovered collections
  will now inherit the readonly property
* FIX ikhal will not wrap date headers into the next line in narrow terminals
* FIX `configure` should only suggest valid default collection names
* NEW the `configure` command can now set up vdirsyncer
* NEW better error message for misuses of `at` and `list`
* NEW `discover` collection type now supports `**` (arbitrary depths)
* NEW Add testing for Python 3.11

0.10.5
======
2022-06-26

* FIX support for tzlocal >= 4.0
* FIX ability to show an event's calendar in ikhal
* FIX an error logging for certain broken icalendar events that made ikhal crash
  after editing those events
* NEW Add widget to interactive event editor that allows adding attendees as
  comma separated list of email addresses
* FIX event creation for events after the second next DST transition

* NEW Add support for Python 3.10
* CHANGE `search`, `at`, and `list` don't print "No events" anymore if no matching
  events are found
* NEW Add option to use `multiple` color only when not all calendar colors can
  be displayed.
* CHANGE we are not shipping a zsh completion file anymore but provide
  documentation on how to generate completion files for bash, zsh, and fish
  (see the install section of the documentation)

  **Packagers**: please generate and ship those completion files if possible


0.10.4
======
2021-07-29

* DROPPED support for Python 3.5
* CHANGE ikhal: tab (and shift tab) jump from the events back to the calendar
* NEW Add symbol for events with at least one alarm
* FIX URL can now be set/updated from ikhal
* FIX Imported events without an end or duration will now last one day if
  `DTSTART` is a date (as per RFC) or one hour if it is a datetime.

0.10.3
======
2021-04-27

* DROPPED support for Python 3.4
* FIX `khal interactive` now accepts -a/-d options (as documented)
* FIX Strip whitespace when loading `displayname` and `color` files
* FIX Warn when loading events with a recurrence that finishes before it starts
* FIX Warn when loading events with a recurrence that never occurs
* FIX Alarms without descriptions no longer crash `ikhal`
* FIX Display all-day events at the top of the day in `ikhal`
* FIX Keybindings in empty search results no longer crash `ikhal`
* NEW Possibility to add a blank line before day in `khal` with
  `blank_line_before_day` option
* FIX `new` keybinding in search no longer crash `ikhal`
* NEW Improved sorting of events. Sort by `DTSTART`, `DTEND` then `SUMMARY`.
* NEW Add url input and `{url}` template option

0.10.2
======
2020-07-29

* NEW Parse `X-ANNIVERSARY`, `ANNIVERSARY` and `X-ABDATE` fields from vcards
* NEW Add ability to change default event duration with
  `default_event_duration` and `default_dayevent_duration` for a day-long
  event
* NEW Add `{uid}` property to template options in `--format`
* FIX No warning when importing event with Windows timezone format
* FIX Launching an external editor no longer crashes `ikhal`
* UPDATED DEPENDENCY urwid>=1.3.0
* FIX Wrong left pane width calculation in ikal when `frame` is `width` or
  `color` in configuration.
* CHANGE Remove check for timezones in `UNTIL` that aren't in `DTSTART` and
  vice-versa. The check wasn't fulfilling its purpose and was raising warnings
  when no `UNTIL` value was set.

0.10.1
======
2019-03-30

* FIX error with the new color priority system and `discover` calendar type
* FIX search results in ikhal are ordered, same as in `khal search`

0.10.0
======
2019-03-25

* In contrast to what was stated here before, at release time, khal >0.10.0
  supported dateutil 2.7

* NEW DEPENDENCY added click_log  >= 0.2.0
* NEW DEPENDENCY for Python 3.4: typing
* UPDATED DEPENDENCY icalendar>=4.03
* DROPPED support for Python 3.3
* vdirsyncer is still a test dependency (and always has been)

* FIX ordinal numbers in birthday entries (before, all number would end on `th`)
* FIX `search` will no longer break on overwritten events with a master event
* FIX when using short dates, khal infers that you meant next year, when date
  is before today
* FIX Check for multi_uid .ics files in vdirs and don't import those events
  (All .ics files in vdirs should only contain VEVENTS with the same UID.)

* CHANGE only searched configuration file paths are now
  $XDG_CONFIG_HOME/khal/config and $XDG_CONFIG_HOME/khal/khal.conf (deprecated)
* CHANGE removed default command
* CHANGE default date/time formats to be the system's locale's formats
* CHANGE ``--verbose`` flag to ``--verbosity``, allowing finer granularity
* CHANGE `search` will now print one line for every different event in a
  recurrence set, that is one line for the master event, and one line for every
  different overwritten event
* CHANGE khal learned to read .ics files with nonsenscial TZOFFSETs > 24h and
  prints a warning
* CHANGE better error message for a specific kind of invalid config file

* NEW khal learned the ``--logfile/-l LOGFILE`` flag which allows logging to a
  file
* NEW format can now print the duration of an event with `{duration}`
* NEW format supports `{nl}`, `{tab}`, `{bell}`. `{status}` has a whitespace
  like `{cancelled}`
* NEW configuration option: [view]monthdisplay = firstday|firstfullweek,
  if set to 'firstday', khal displays the month name as soon as any day
  in the week is within the new month. If set to 'firstfullweek', khal
  displays the month name only if the first day of the week is within
  the new month.

* NEW ikhal learned to show log messages in the header and in a new log pane,
  access with default keybinding `L`

* NEW python 3.7 is now officially supported.

* NEW configuration option [[per_calendar]]priority = int (default 10). If
  multiple calendars events are on the same day, the day will be colored with
  the color of the calendar with highest priority. If multiple calendars have
  the same highest priority, it falls back to the previous system.

* NEW format can now print the organizer of the event with '(organizer)'

0.9.8
=====
released 2017-10-05

* FIX a bug in ikhal: when editing events and not editing the dates, the end
  time could erroneously be moved to the start time + 1h

0.9.7
=====
released 2017-09-15

* FIX don't crash when editing events with datetime UNTIL properties

0.9.6
=====
released 2017-06-13

* FIX set PRODID to khal/icalendar
* FIX don't crash on updated vcards
* FIX checking for RRULEs we understand
* FIX after editing an event in ikhal, make sure both the calendar and the
  eventcolumn are focused on the new date
* FIX no more crashes if only one event which is an overwritten instance is
  present in an .ics file
* FIX .ics files containing only overwritten instances are not expanded anymore,
  even if they contain a RRULE or RDATE
* FIX valid UNTIL entry for recurring datetime events

* CHANGE the symbol used for indicating a recurring event now has a space in
  front of it, also the ascii version changed to `(R)`
* CHANGE birthdays on leap 29th of February are shown on 1st of March in
  non-leap years

* NEW import and printics will read from stdin if not filename(s) are provided.
* NEW new entry points recommended for packagers to use.
* NEW support keyword `yesterday` for querying and creating events

0.9.5
======
released 2017-04-08

* FIX khal new -i does not crash anymore
* FIX make tests run with latest pytz (2017.2)

0.9.4
=====
released 2017-03-30

* FIX ikhal's event editor now warns before allowing to edit recurrence rules it
  doesn't understand

* CHANGE improved the initial configuration wizard

* CHANGE improved ikhal's `light` color scheme
* NEW ikhal's event editor now allows better editing of recurrence rules,
  including INTERVALs, end dates, and more
* NEW ikhal will now check if any configured vdir has been updated, and, if
  applicable, refresh its UI to reflect the latest changes

0.9.3
=====
released 2017-03-06

* FIX `list` (and commands based on it like `calendar`, `at`, and `search`)
  crashed if `--notstarted` was given and allday events were found (introduced
  in 0.9.2)
* FIX `list --notstarted` (and commands based on it) would show events only on
  the first day of their occurrence and not on all further days
* FIX `configure` would crash if neither "import config from vdirsyncer" nor
  "create locale vdir" was selected
* FIX `at` will now show an error message if a date instead of a datetime is
  given
* FIX `at`'s default header will now show the datetime queried for (instead of
  just the date)
* FIX validate vdir metadata in color files
* FIX show the actually configured keybindings in ikhal

* NEW khal will now show cancelled events with a big CANCELLED in front (can be
  configured via event formatting)
* NEW ikhal supports editing an event's raw icalendar content in an external
  editor ($EDITOR), default keybinding is `alt + shift + e`. Only use this, if
  you know what you are doing, the icalendar library we use doesn't do a lot of
  validation, it silently disregards most invalid data.

0.9.2
=====
released 2017-02-13

* FIX if weekstart != 0 ikhal would show wrong weekday names
* FIX allday events added with `khal new DATE TIMEDELTA` (e.g., 2017-01-18 3d)
  were lasting one day too long
* FIX no more crashes when using timezones that have a constant UTC offset (like
  UTC itself)
* FIX updated outdated zsh completion file
* FIX display search results for events with neither DTEND nor DURATION
* FIX display search results that are all-day events
* in ikhal, update the date-titles on date change
* FIX printing a new event's path if [default] print_new = path
* FIX width of calendar in `khal calendar` was off by two if locale.weeknumbers
  was set to "right"

* CHANGED default `agenda_day_format` to include the actual date of the day

* NEW configuration option: [view]dynamic_days = True, if set to False, ikhal's
  right column behaves similar as it did in 0.8.x

0.9.1
=====
released 2017-01-25

* FIX detecting not understood timezone information failed on python 3.6, this may lead to
  erroneous offsets in start and end times for those events, as those datetimes
  were treated as if they were in the system's local time, not as if they are in
  the (possibly) configured default_timezone.

* python 3.6 is now officially supported

0.9.0
=====
released 2017-01-24

Dependency Changes
------------------
* vdirsyncer isn't a hard dependency any more

Bug Fixes
---------
* fixed various bugs in `configure`
* fix bug in `new` that surfaces when date(time)format does contain a year
* fix bug in `import` that allows importing into read-only and/or non-default calendar
* fix how color discovered in calendars

Backwards Incompatibilities
---------------------------
* calendar path is now a glob without recursion for discover, if your calendars
  are no longer found, please consult the documentation (Taylor Money)
* `at` command now works like `list` with a timedelta of `0m`, this means that
  `at` will no longer print events that end at exactly the time asked for
  (Taylor Money)
* renamed `agenda` to `list` (Taylor Money)
* removed `days` configuration option in favor of `timedelta`, see
  documentation for details (Taylor Money)
* configuration file path $XDG_CONFIG_HOME/khal/config is now supported and
  $XDG_CONFIG_HOME/khal/khal.conf deprecated
* ikhal: introduction of three different new frame styles, new allowed values for
  `[view] frame` are `False`, `width`, `color`, `top` (with default `False`),
  `True` isn't allowed any more, please provide feedback over the usual channels
  if and which of those you consider useful as some of those might be removed in
  future releases (Christian Geier)
* removed configuration variable `encoding` (in section [locale]), the correct
  locale should now be figured out automatically (Markus Unterwaditzer)
* events that start and end at the same time are now displayed as if their
  duration was one hour instead of one day (Guilhem Saurel)

Enhancements
------------
* (nearly) all commands allow formatting of how events are printed with
  `--format`, also see the new configuration options `event_format`,
  `agenda_event_format`, `agenda_day_format` (Taylor Money)
* support for categories (and add `-g` flag for `khal new`) (Pierre David)
* search results are now sorted by start date (Taylor Money)
* added command `edit`, which also allows deletion of events (Taylor Money)
* `new` has interactive option (Taylor Money)
* `import` can now import multiple files at once (Christian Geier)

ikhal
-----
* BUGFIX no more crashing if invalid date is entered and mini-calendar displayed
* make keybinding for quitting configurable, defaults to *q* and *Q*, escape
  only backtracks to last pane but doesn't exit khal anymore (Christian Geier)
* default keybinding changed: `tab` no longer shows details of focused events
  and does not open the event editor either (Christian Geier)
* right column changed, it will now show as many days/events as fit, if users move
  to another date (while the event column is in focus), that date should be
  highlighted in the calendar (Christian Geier)
* cursor indicates which element is selected

0.8.4
=====
released 2016-10-06

* **IMPORTANT BUGFIX** fixed a bug that lead to imported events being
  erroneously shifted if they had a timezone identifier that wasn't an Olson
  database identifier. All users are advised to upgrade as soon as possible. To
  see if you are affected by this and how to resolve any issues, please see the
  release announcement (khal/doc/source/news/khal084.rst or
  http://lostpackets.de/khal/news/khal084.html). Thanks to Wayne Werner for
  finding and reporting this bug.

0.8.3
=====
released 2016-08-28

* fixed some bugs in the test suite on different operating systems
* fixed a check for icalendar files containing RDATEs

0.8.2
=====
released on 2016-05-16

* fixed some bugs in `configure` that would lead to invalid configuration files
  and crashes (Christian Geier)
* fixed detecting of icalendar version (Markus Unterwaditzer)

0.8.1
=====
released on 2016-04-13

* fix bug in CalendarWidget.set_focus_date() (Christian Geier)

0.8.0
=====
released on 2016-04-13

* BREAKING CHANGE: python 2 is no longer supported (Hugo Osvaldo Barrera)
* updated dependency: vdirsyncer >= 0.5.2
* make tests work with icalendar 3.9.2 (no functional changes) (Christian Geier)
* new dependency: freezegun (only for running the tests)
* khal's git repository moved to https://github.com/pimutils/khal

* support for showing the birthday of contacts with no FN property (Hugo
  Osvaldo Barrera)
* increased start up time when coloring is enabled (Christian Geier)
* improved color support (256 colors and 24-bit colors), see configuration
  documentation for details (Sebastian Hamann)
* renamed color `grey` to `gray` (Sebastian Hamann)
* in `khal new` treat 24:00 as the end of a day/00:00 of the next (Christian Geier)
* new allowed value for a calendar's color: `auto` (also the new default), if
  set, khal will try to read a file called `color` from that calendar's vdir (see
  vdirsyncer's documentation on `metasync`). If that file is not present or its
  contents is not understood, the default color will be used (Christian Geier)
* new allowed value for calendar's type: `discover`, if set, khal will
  (recursively) search that calendar's path for valid vdirs and add those to
  the configured calendars (Christian Geier)
* new command `configure` which should help new users set up a configuration
  file (Christian Geier)
* warn user when parsing broken icalendar files, this requires icalendar > 3.9.2
  (Christian Geier)
* khal will now strip all ANSI escape codes when it detects that stdout is no
  tty, this behaviour can be overwritten with the new options --color/ --no-color
  (Markus Unterwaditzer)
* calendar and agenda have a new option --week, if set all events from current week
  (or the week containing the given date) are shown (Stephan Weller)
* new option --alarm DURATION for `new` (Max Voit)

ikhal
-----
* basic export of events from event editor pane and from event lists (default
  keybinding: *e*) (Filip Pytloun)
* pressing *enter* in a date editing widget will now open a small calendar
  widget, arrow keys can be used to select a date, enter (or escape) will close
  it again (Christian Geier)
* in highlight/date range selection mode the other end can be selected, default
  keybinding `o` (as in *Other*) (Christian Geier)
* basic search is now supported (default keybinding `/`) (Christian Geier)
* in the event editor and pop-up Dialogs select the next (previous) item with tab
  (shift tab) (Christian Geier)
* only allow saving when starttime < endtime (Christian Geier)
* the event editor now allows editing of alarms (but khal will not actually
  alarm you at the given time) (Johannes Wienke)


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
  in another calendar (but no data lost incurred) (Christian Geier)

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

* new command `search` allows searching for events
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
  noticeable when running khal for the first time or after a deleting the
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
      will be build in *build/html* or *build/man* respectively)
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
