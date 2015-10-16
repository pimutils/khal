Usage
=====

Khal offers a set of commands, most importantly :command:`agenda`,
:command:`calendar`, :command:`interactive`, :command:`new`,
:command:`printcalendars`, :command:`printformats`, and :command:`search`. See
below for a description of what every command does. Calling :program:`khal`
without any command will invoke the default command, which can be specified in
the configuration file.


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

.. option:: -v

        Be more verbose (e.g. print debugging information)

.. option:: -c CONFIGFILE

        Use an alternate configuration file

.. option:: -a CALENDAR

        Specify a calendar to use (which must be configured in the configuration
        file), can be used several times. Calendars not specified will be
        disregarded for this run.

.. option:: -d CALENDAR

        Specifiy a calendar which will be disregarded for this run, can be used
        several times.


dates
-----
Almost everywhere khal accepts dates, khal should recognize relative date names
like *today*, *tomorrow* and the names of the days of the week (also in
three letters abbreviated form). Week day names get interpreted as the date of
the next occurrence of a day with that name. The name of the current day gets
interpreted as that date *next* week (i.e. seven days from now).

Commands
--------

agenda
******
shows all events scheduled for given dates. ``khal agenda`` should understand
the following syntax:

::

    khal agenda [-a CALENDAR ... | -d CALENDAR ...] [--days N] [DATE ...]

If no dates are supplied as arguments, today and tomorrow are used. Dates must
be given in the format specified in khal's config file as *dateformat* or
*longdateformat*. If *dateformat* is used, the current year is implied.

.. option:: --days N

        Specify how many days' (following each DATE) events should be shown.

at
**
shows all events scheduled for a given datetime. ``khal at`` should be supplied
with a date and time, a time (the date is then assumed to be today) or the
string *now*. ``at`` defaults to *now*.

::

        khal at [-a CALENDAR ... | -d CALENDAR ...] [DATETIME | now]

calendar
********
shows a calendar (similiar to :manpage:`cal(1)`) and agenda. ``khal calendar``
should understand the following syntax:

::

        khal calendar [-a CALENDAR ... | -d CALENDAR ...] [--days N] [DATE ...]

Date selection works exactly as for ``khal agenda``. The displayed calendar
contains three consecutive months, where the first month is the month
containing the first given date. If today is included, it is highlighted.
Have a look at ``khal agenda`` for a descrption of the options.


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
:command:`ikhal`.

Use the arrow keys to navigate in the calendar. Press 'tab' or 'enter' to move
the focus into the events column and 'left arrow' to return the focus to the
calendar area. You can navigate the events column with the up and down arrows
and view an event via pressing 'enter'. Pressing 'd' will delete an event (a 'D'
will appear in front of the events description, or 'RO' if you cannot delete
that event). Pressing 'd' again will undelete that event.

When viewing an event's details, pressing 'enter' again will open the
currently selected event in a simple event editor; you can navigate with the
arrow keys again. As long as the event has not been edited you can leave the
editor with pressing 'escape'. Once it has been edited you need to move down the
'Cancel' button and press the 'enter' key to discard your edits or press the
'Save' button to save your edits (and upload them on the next sync).

While the calendar area is focused, pressing 'n' will add a new event on the
currently selected date.


new
***
allows for adding new events. ``khal new`` should understand the following syntax:

::

    khal new [-a CALENDAR] [OPTIONS] startdatetime [enddatetime] [timezone] summary [description]

where start- and enddatetime are either datetimes, times, or keywords and times
in the formats defined in the config file. If no calendar is given via
:option:`-a`, the default calendar is used. :command:`new` does not support
:option:`-d` and also :option:`-a` may only be used once.

:command:`new` accepts these combinations for stard and endtimes (specifying
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

The exact format of langdatetimeformat, datetimeformat, timeformat,
longdateformat and dateformat can be configured in the configuration file.
Valid keywords for dates are *today*, *tomorrow*, the English name of all seven
weekdays and their three letter abbreviations (their next occurence is used).

If no end is given, the default length of one hour or one day (for all-day
events) is used. If only a start time is given the new event is assumed to be
starting today. If only a time is given for the event to end on, the event ends
on the same day it starts on, unless that would make the event end before it has
started, then the next day is used as end date

If the **summary** contains the string `::`, everything after `::` is taken as
the **description** of the new event, i.e., the "body" of the event (and `::`
will be removed).

Options
"""""""
* **-l, --location=LOCATION** specify where this event will be held.

* **-r, --repeat=RRULE** specify if and how this event should be recurring.
  Valid values for *RRULE* are `daily`, `weekly`, `monthly`
  and `yearly`

* **-u, --until=UNTIL** specify until when a recurring event should run

Examples
""""""""
::

    khal new 18:00 Awesome Event

adds a new event starting today at 18:00 with summary 'awesome event' (lasting
for the default time of one hour) to the default calendar

::

    khal new tomorrow 16:30 Coffee Break

adds a new event tomorrow at 16:30

::

    khal new 25.10. 16:00 18:00 Another Event :: with Alice and Bob

adds a new event on 25th of October lasting from 16:00 to 18:00 with an
additional description

::

    khal new -a work 26.07. Great Event -r weekly

adds a new all day event on 26th of July to the calendar *work* which recurs
every week.

printcalendars
**************
prints a list of all configured calendars.


printformats
************
prints a fixed date (*2013-12-11 10:09*) in all configured date(time) formats.
This is supposed to help check if those formats are configured as intended.

search
******
search for events matching a search string and print them. Currently recurring
events are only printed once. No advanced search features are currently
supported.

The command

::

    khal search party

prints all events matching `party`.
