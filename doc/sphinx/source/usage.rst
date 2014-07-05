Usage
=====

Khal is a calendar program for the terminal for viewing, adding and editing
events and calendars. Khal is build on the iCalendar_ and vdir_ (allowing the
use of vdirsyncer_ for CalDAV compatibility) standards.

Khal offers a set of commands, namely :command:`calendar`, :command:`agenda`,
:command:`new`, :command:`printcalendars`, and :command:`interactive`. See
below for a description of what each of these commands does. Calling
:program:`khal` without any command will invoke the default command, which can
be specified in the config file.


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

Commands
--------


agenda
******
shows all events scheduled for given dates. ``khal agenda`` should understand
the following syntax:

::

    khal agenda [-a CALENDAR ... | -d CALENDAR ...] [DATE ...]

If no dates are supplied as arguments, today and tomorrow are used. Dates must
be given in the format specified in khal's config file as *dateformat* or
*longdateformat*. If dateformat is used, the current year is implied.


calendar
********
shows a calendar (similiar to :manpage:`cal(1)`) and agenda. ``khal calendar``
should understand the following syntax:

::

        khal calendar [-a CALENDAR ... | -d CALENDAR ...] [DATE ...]

Date selection works exactly as for ``khal agenda``. The displayed calendar
contains three consecutive months, where the first month is the month
containing the first given date. If today is included, it is highlighted.

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
allows for quick adding of new events. ``khal new`` should understand the following syntax:

::

    khal new [-a CALENDAR] startdatetime [enddatetime] summary [description]

where start- and enddatetime are either datetimes or times in the formats defined
in the config file. If no calendar is given via :option:`-a`, the default
calendar is used. :command:`new` does no support :option:`-d` and also
:option:`-a` may only be used once.

Start- and enddatetime can be one of the following:

* **datetime datetime:** start and end datetime specified, if no year is given
  (like the non-long version of dateformat, see config file, should allow),
  this year is used.

* **datetime time:** end date will be same as start date, unless that would make
  the event end before it has started, then the next day is used as end date

* **datetime:** event will last for defaulttime

* **time time:** event starting today at the first time and ending today at the
  second time, unless that would make the event end before it has started, then
  the next day is used as end date

* **time:** event starting today at time, lasting for the default length

* **date date:** all day event starting on the first and ending on the last
  event

* **date:** all day event starting at given date and lasting for default length

**description** is a string started by `::` (which will be removed) and will be
used as the new event's *description*, i.d., the body of the event.

At the moment default length is either 1 hour or 1 day (should be configurable soon,
too).

Some examples:

::

    khal new 18:00 Awesome Event

adds a new event starting today at 18:00 with summary 'awesome event' (lasting
for the default time of one hour) to the default calendar

::

    khal new 25.10. 16:00 18:00 Another Event :: with Alice and Bob

adds a new event on 25th of October lasting from 16:00 to 18:00 with an
additional description

::

    khal new -a work 26.07. Great Event

adds a new all day event on 26th of July to the calendar *work*.

printcalendars
**************

prints a list of all configured calendars.
