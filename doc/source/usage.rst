Usage
=====
Khal offers a set of commands, most importantly :command:`list`,
:command:`calendar`, :command:`interactive`, :command:`new`,
:command:`printcalendars`, :command:`printformats`, and :command:`search`. See
below for a description of what every command does. :program:`khal` does
currently not support any default command, i.e., run a command, even though none
has been specified. This is intentional.


Options
-------
:program:`khal` (without any commands) has some options to print some
information about :program:`khal`:

.. option:: --version

        Prints khal's version number and exits

.. option:: -h, --help

        Prints a summary of khal's options and commands and then exits

Several options are common to almost all of :program:`khal`'s commands
(exceptions are described below):

.. option:: -v, --verbosity LVL

        Configure verbosity (e.g. print debugging information), `LVL` needs to
        be one of CRITICAL, ERROR, WARNING, INFO, or DEBUG.

.. option:: -l, --logfile LOFILE

        Use logfile `LOGFILE` for logging, default is logging to stdout.

.. option:: -c CONFIGFILE

        Use an alternate configuration file.

.. option:: -a CALENDAR

        Specify a calendar to use (which must be configured in the configuration
        file), can be used several times. Calendars not specified will be
        disregarded for this run.

.. option:: -d CALENDAR

        Specify a calendar which will be disregarded for this run, can be used
        several times.

.. option:: --color/--no-color

       :program:`khal` will detect if standard output is not a tty, e.g., you
       redirect khal's output into a file, and if so remove all
       highlighting/coloring from its output. Use :option:`--color` if you want
       to force highlighting/coloring and :option:`--no-color <--color>` if you want
       coloring always removed.


.. option:: --format FORMAT

   For all of khal's commands that print events, the formatting of that event
   can be specified with this option.  ``FORMAT`` is a template
   string, in which identifiers delimited by curly braces (`{}`) will be
   expanded to an event's properties.  ``FORMAT`` supports all formatting
   options offered by python's `str.format()`_ (as it is used internally).
   The available template options are:


   title
        The title of the event.

   description
        The description of the event.

   description-separator
        A separator: " :: " that appears when there is a description.

   uid
        The UID of the event.

   start
        The start datetime in datetimeformat.

   start-long
        The start datetime in longdatetimeformat.

   start-date
        The start date in dateformat.

   start-date-long
        The start date in longdateformat.

   start-time
        The start time in timeformat.

   end
        The end datetime in datetimeformat.

   end-long
        The end datetime in longdatetimeformat.

   end-date
        The end date in dateformat.

   end-date-long
        The end date in longdateformat.

   end-time
        The end time in timeformat.

   repeat-symbol
        A repeating symbol (loop arrow) if the event is repeating.

   alarm-symbol
        An alarm symbol (alarm clock) if the event has at least one alarm.

   location
        The event location.

   calendar
        The calendar name.

   calendar-color
        Changes the output color to the calendar's color.

   start-style
        The start time in timeformat OR an appropriate symbol.

   to-style
        A hyphen "-" or nothing such that it appropriately fits between
        start-style and end-style.

   end-style
        The end time in timeformat OR an appropriate symbol.

   start-end-time-style
        A concatenation of start-style, to-style, and end-style OR an
        appropriate symbol.

   end-necessary
        For an allday event this is an empty string unless the end date and
        start date are different. For a non-allday event this will show the
        time or the datetime if the event start and end date are different.

   end-necessary-long
        Same as end-necessary but uses datelong and datetimelong.

   status
       The status of the event (if this event has one), something like
       `CONFIRMED` or `CANCELLED`.

    status-symbol
       The status of the event as a symbol, `✓` or `✗` or `?`.

    partstat-symbol
        The participation status of the event as a symbol, `✓` or `✗` or `?`.

   cancelled
       The string `CANCELLED` (plus one blank) if the event's status is
       cancelled, otherwise nothing.

   organizer
       The organizer of the event. If the format has CN then it returns "CN (email)"
       if CN does not exist it returns just the email string. Example:
       ORGANIZER;CN=Name Surname:mailto:name@mail.com
       returns
       Name Surname (name@mail.com)
       and if it has no CN attribute it returns the last element after the colon:
       ORGANIZER;SENT-BY="mailto:toemail@mail.com":mailto:name@mail.com
       returns
       name@mail.com

   url
       The URL embedded in the event, otherwise nothing.

   url-separator
        A separator: " :: " that appears when there is a url.

   duration
       The duration of the event in terms of days, hours, months, and seconds
       (abbreviated to `d`, `h`, `m`, and `s` respectively).

   repeat-pattern
       The raw iCal recurrence rule if the event is repeating.

   all-day
       A boolean indicating whether it is an all-day event or not.

   categories
       The categories of the event.

   By default, all-day events have no times. To see a start and end time anyway simply
   add `-full` to the end of any template with start/end or duration, for instance
   `start-time` becomes `start-time-full` and will always show start and end times (instead
   of being empty for all-day events).

   In addition, there are colors: `black`, `red`, `green`, `yellow`, `blue`,
   `magenta`, `cyan`, `white` (and their bold versions: `red-bold`, etc.). There
   is also `reset`, which clears the styling, and `bold`, which is the normal
   bold.

   A few control codes are exposed.  You can access newline (`nl`), 'tab', and 'bell'.
   Control codes, such as `nl`, are best used with `--list` mode.

   Below is an example command which prints the title and description of all events today.

   ::

           khal list --format "{title} {description}"


.. option:: --json FIELD ...

   Works similar to :option:`--format`, but instead of defining a format string a JSON
   object is created for each specified field. The matching events are collected into
   a JSON array. This option accepts the following subset of :option:`--format`
   template options::

           title, description, uid, start, start-long, start-date,
           start-date-long, start-time, end, end-long, end-date,
           end-date-long, end-time, start-full, start-long-full,
           start-date-full, start-date-long-full, start-time-full,
           end-full, end-long-full, end-date-full, end-date-long-full,
           end-time-full, repeat-symbol, location, calendar,
           calendar-color, start-style, to-style, end-style,
           start-end-time-style, end-necessary, end-necessary-long,
           status, cancelled, organizer, url, duration, duration-full,
           repeat-pattern, all-day, categories


   Note that `calendar-color` will be the actual color name rather than the ANSI color code,
   and the `repeat-symbol`, `status`, and `cancelled` values will have leading/trailing
   whitespace stripped.  Additionally, if only the special value `all` is specified then
   all fields will be enabled.

   Below is an example command which prints a JSON list of objects containing the title and
   description of all events today.

    .. code-block:: console

           khal list --json title --json description


.. option:: --day-format DAYFORMAT

   works similar to :option:`--format`, but for day headings. It only has a few
   options (in addition to all the color options):

   date
        The date in dateformat.

   date-long
        The date in longdateformat.

   name
        The date's name (`Monday`, `Tuesday`,…) or `today` or `tomorrow`.

   If the `--day-format` is passed an empty string then it will not print the
   day headers (for an empty line pass in a whitespace character).



dates
-----
Almost everywhere khal accepts dates, khal should recognize relative date names
like *today*, *tomorrow* and the names of the days of the week (also in
three letters abbreviated form). Week day names get interpreted as the date of
the next occurrence of a day with that name. The name of the current day gets
interpreted as that date *next* week (i.e. seven days from now).

If a short datetime format is used (no year is given), khal will interpret the
date to be in the future. The inferred it might be in the next year if the given
date has already passed in the current year.

Commands
--------

list
****
shows all events scheduled for a given date (or datetime) range, with custom
formatting::

        khal list [-a CALENDAR ... | -d CALENDAR ...]
        [--format FORMAT] [--json FIELD ...] [--day-format DAYFORMAT]
        [--once] [--notstarted] [START [END | DELTA] ]

START and END can both be given as dates, datetimes or times (it is assumed
today is meant in the case of only a given time) in the formats configured in
the configuration file.  If END is not given, midnight of the start date is
assumed. Today is used for START if it is not explicitly given.  If DELTA, a
(date)time range in the format `I{m,h,d}`, where `I` is an integer and `m` means
minutes, `h` means hours, and `d` means days, is given, END is assumed to be
START + DELTA.  A value of `eod` is also accepted as DELTA and means the end of
day of the start date. In addition, the DELTA `week` may be used to specify that
the daterange should actually be the week containing the START.

The `--once` option only allows events to appear once even if they are on
multiple days. With the `--notstarted` option only events are shown that start
after `START`.

**Some examples**

Including or excluding specific calendars:

* `khal list -d soccer` will display events, in list form, from every calendar except "soccer."
* `khal list -a soccer` will display events, in list form, from only the "soccer" calendar.

Working with date ranges:

* `khal list -a soccer today 30d` will show all events in next 30 days (from the "soccer" calendar).
* `khal list 2019-12-01 31d` will show all all events for the 31 days following Dec 1, 2019.

at
**
shows all events scheduled for a given datetime. ``khal at`` should be supplied
with a date and time, a time (the date is then assumed to be today) or the
string *now*. ``at`` defaults to *now*. The ``at`` command works just like the
``list`` command, except it has an implicit end time of zero minutes after the
start.

::

        khal at [-a CALENDAR ... | -d CALENDAR ...]
        [--format FORMAT] [--json FIELD ...]
        [--notstarted] [[START DATE] TIME | now]

calendar
********
shows a calendar (similar to :manpage:`cal(1)`) and list. ``khal calendar``
should understand the following syntax:

::

        khal calendar [-a CALENDAR ... | -d CALENDAR ...] [START DATETIME]
        [END DATETIME]

Date selection works exactly as for ``khal list``. The displayed calendar
contains three consecutive months, where the first month is the month
containing the first given date. If today is included, it is highlighted.
Have a look at ``khal list`` for a description of the options.

configure
*********
will help users creating an initial configuration file. :command:`configure` will
refuse to run if there already is a configuration file.

import
******
lets the user import ``.ics`` files with the following syntax:

::

        khal import [-a CALENDAR] [--batch] [--random-uid|-r] ICSFILE

If an event with the same UID is already present in the (implicitly)
selected calendar ``khal import`` will ask before updating (i.e. overwriting)
that old event with the imported one, unless --batch is given, than it will
always update. If this behaviour is not desired, use the `--random-uid` flag to
generate a new, random UID.  If no calendar is specified (and not `--batch`),
you will be asked to choose a calendar. You can either enter the number printed
behind each calendar's name or any unique prefix of a calendar's name.


interactive
***********
invokes the interactive version of khal, can also be invoked by calling
:command:`ikhal`. While ikhal can be used entirely with the keyboard, some
elements respond if clicked on with a mouse (mostly by being selected).

When the calendar on the left is in focus, you can

 * move through the calendar (default keybindings are the arrow keys, :kbd:`space` and
   :kbd:`backspace`, those keybindings are configurable in the config file)
 * focus on the right column by pressing :kbd:`tab` or :kbd:`enter`
 * re-focus on the current date, default keybinding :kbd:`t` as in today
 * marking a date range, default keybinding :kbd:`v`, as in visual, think visual
   mode in Vim, pressing :kbd:`esc` escapes this visual mode
 * if in visual mode, you can select the other end of the currently marked
   range, default keybinding :kbd:`o` as in other (again as in Vim)
 * create a new event on the currently focused day (or date range if a range is
   selected), default keybinding :kbd:`n` as in new
 * search for events, default keybinding :kbd:`/`, a pop-up will ask for your
   search term

When an event list is in focus, you can

 * view an event's details with pressing :kbd:`enter` (or :kbd:`tab`) and edit it with pressing
   :kbd:`enter` (or :kbd:`tab`) again (if ``[default] event_view_always_visible`` is set to
   True, the event in focus will always be shown in detail)
 * toggle an event's deletion status, default keybinding :kbd:`d` as in delete,
   events marked for deletion will appear with a :kbd:`D` in front and will be
   deleted when khal exits.
 * duplicate the selected event, default keybinding :kbd:`p` as in duplicate
   (d was already taken)
 * export the selected event, default keybinding :kbd:`e`

In the event editor, you can

* jump to the next (previous) selectable element with pressing :kbd:`tab`
  (:kbd:`shift+tab`)
* quick save, default keybinding :kbd:`meta+enter` (:kbd:`meta` will probably be :kbd:`alt`)
* use some common editing short cuts in most text fields (:kbd:`ctrl+w` deletes word
  before cursor, :kbd:`ctrl+u` (:kbd:`ctrl+k`) deletes till the beginning (end) of the
  line, :kbd:`ctrl+a` (:kbd:`ctrl+e`) will jump to the beginning (end) of the line
* in the date and time fields you can increment and decrement the number under
  the cursor with :kbd:`ctrl+a` and :kbd:`ctrl+x` (time in 15 minute steps)
* in the date fields you can access a miniature calendar by pressing `enter`
* activate actions by pressing :kbd:`enter` on text enclosed by angled brackets, e.g.
  :guilabel:`< Save >` (sometimes this might open a pop up)

Pressing :kbd:`esc` will cancel the current action and/or take you back to the
previously shown pane (i.e. what you see when you open ikhal), if you are at the
start pane, ikhal will quit on pressing :kbd:`esc` again.


new
***
allows for adding new events. ``khal new`` should understand the following syntax:

::

    khal new [-a CALENDAR] [OPTIONS] [START [END | DELTA] [TIMEZONE] SUMMARY
    [:: DESCRIPTION]]

where start- and enddatetime are either datetimes, times, or keywords and times
in the formats defined in the config file. If no calendar is given via
:option:`-a`, the default calendar is used. :command:`new` does not support
:option:`-d` and also :option:`-a` may only be used once.

:command:`new` accepts these combinations for start and endtimes (specifying
the end is always optional):

 * `datetime [datetime|time] [timezone]`
 * `time [time] [timezone]`
 * `date [date]`

where the formats for datetime and time are as follows:

 * `datetime = (longdatetimeformat|datetimeformat|keyword-date timeformat)`
 * `time = timeformat`
 * `date = (longdateformat|dateformat)`

and `timezone`, which describes the timezone the events start and end time are
in, should be a valid Olson DB identifier (like `Europe/Berlin` or
`America/New_York`. If no timezone is given, the *defaulttimezone* as
configured in the configuration file is used instead.

The exact format of longdatetimeformat, datetimeformat, timeformat,
longdateformat and dateformat can be configured in the configuration file.
Valid keywords for dates are *today*, *tomorrow*, the English name of all seven
weekdays and their three letter abbreviations (their next occurrence is used).

If no end is given, the default length of one hour or one day (for all-day
events) is used. If only a start time is given the new event is assumed to be
starting today. If only a time is given for the event to end on, the event ends
on the same day it starts on, unless that would make the event end before it has
started, then the next day is used as end date

If a 24:00 time is configured (timeformat = %H:%M) an end time of `24:00` is
accepted as the end of a given date.

If the **summary** contains the string `::`, everything after `::` is taken as
the **description** of the new event, i.e., the "body" of the event (and `::`
will be removed).

Passing the option :option:`--interactive` (:option:`-i`) makes all arguments
optional and interactively prompts for required fields, then the event may be
edited, the same way as in the `edit` command.

Options
"""""""
* **-l, --location=LOCATION** specify where this event will be held.

* **-g, --categories=CATEGORIES** specify which categories this event belongs to.
  Comma separated list of categories. Beware: some servers (e.g. SOGo) do not support multiple categories.

* **-r, --repeat=RRULE** specify if and how this event should be recurring.
  Valid values for *RRULE* are `daily`, `weekly`, `monthly`
  and `yearly`

* **-u, --until=UNTIL** specify until when a recurring event should run

* **--url** specify the URL element of the event

* **--alarms DURATION,...** will add alarm times as DELTAs comma separated for this event,
  *DURATION* should look like `1day 10minutes` or `1d3H10m`, negative
  *DURATIONs* will set alarm after the start of the event.

Examples
""""""""
These may need to be adapted for your configuration and/or locale (START and END
need to match the format configured). See :command:`printformats`.  ::

    khal new 18:00 Awesome Event

adds a new event starting today at 18:00 with summary 'awesome event' (lasting
for the default time of one hour) to the default calendar

::

    khal new tomorrow 16:30 Coffee Break

adds a new event tomorrow at 16:30

::

    khal new 25.10. 18:00 24:00 Another Event :: with Alice and Bob

adds a new event on 25th of October lasting from 18:00 to 24:00 with an
additional description

::

    khal new -a work 26.07. Great Event -g meeting -r weekly

adds a new all day event on 26th of July to the calendar *work* in the *meeting*
category, which recurs every week.


edit
****
an interactive command for editing and deleting events using a search string

::

    khal edit [--show-past] event_search_string

the command will loop through all events that match the search string,
prompting the user to delete, or change attributes.

printcalendars
**************
prints a list of all configured calendars.


printformats
************
prints a fixed date (*2013-12-21 21:45*) in all configured date(time) formats.
This is supposed to help check if those formats are configured as intended.

search
******
search for events matching a search string and print them.  Currently, search
will print one line for every different event in a recurrence set, that is one
line for the master event, and one line for every different overwritten event.
No advanced search features are currently supported.

The command

::

    khal search party

prints all events matching `party`.

.. _str.format(): https://docs.python.org/3/library/string.html#formatstrings
