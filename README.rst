About
=====

.. image:: https://travis-ci.org/geier/khal.svg?branch=master
    :target: https://travis-ci.org/geier/khal

*Khal* is a standards based CLI (console) calendar program. CalDAV_ compatibiliy
is achieved by using vdir_/vdirsyncer_ as a backend, `allowing syncing of
calendars with a variety of other programs on a host of different platforms`__.

*khal* is currently in an early stage of development, has a limited feature set
and is probably full of bugs. If you do try it out, please make sure you have a
backup of your date and please report back any bugs you might encounter.

.. image:: http://lostpackets.de/images/khal.png

Features
--------
(or rather: limitations)

- khal can read and write events/icalendars to vdir_
- fast and easy way to add new events
- ikhal (interactive khal) shows and edit events interactively
- simple recurring events support (no exceptions just yet)
- you cannot edit the timezones of events
- khal should run on all major
  operating systems [1]_ (has been tested on FreeBSD and Debian GNU/Linux)


.. [1] except for Microsoft Windows

Feedback
--------
Please do provide feedback if *khal* works for you or even more importantly
if it doesn't. You can reach me by email at khal (at) lostpackets (dot) de
, by jabber/XMPP at geier (at) jabber (dot) ccc (dot) de or via github_.

.. _vdir: https://github.com/untitaker/vdir
.. _vdirsyncer: https://github.com/untitaker/vdirsyncer
.. _CalDAV: http://en.wikipedia.org/wiki/CalDAV
.. _github: https://github.com/geier/khal/
.. __: http://en.wikipedia.org/wiki/Comparison_of_CalDAV_and_CardDAV_implementations

Usage
-----

install
*******

You can install *khal* from source by executing::

     pip install git+git://github.com/geier/khal.git

Make sure you have ``sqlite3`` (normally available by default), icalendar_, urwid
(>0.9) and ``pyxdg`` installed.

khal has so far been successfully tested on recent versions of FreeBSD,
NetBSD, Debian and Ubuntu with python 2.7.

.. _icalendar: https://github.com/collective/icalendar

configure
*********

copy ``khal.conf.sample`` to ``~/.khal/khal.conf`` or
``~/.config/khal/khal.conf`` and edit to your liking.

syncing
*******

To get *khal* working with CalDAV you will first need to setup vdirsyncer_.
After each start *khal* will automatically check if anything has changed and
automatically update its caching db (this may take some time after the initial
sync, especially for large calendar collections). Therefore you might want to
execute *khal* automatically after syncing with vdirsyncer (e.g. via cron).

.. _vdirsyncer: https://github.com/untitaker/vdirsyncer

basic usage
***********

::

    khal calendar

will show a calendar of this and the next two month and today's and tomorrow's events

::

    khal agenda

will show today's and tomorrow's events

::

    khal interactive

or 

::

    ikhal

opens an interactive calendar browser, showing all events on the selected day.
See below for usage notes on ikhal.


`khal` can be configured to execute on command (calendar, agenda or interactive)
when no other command is given (see the provided example config).

quick event adding
******************

::

    khal new 18:00 Awesome Event

adds a new event starting today at 18:00 with summary 'awesome event' (lasting
for the default time of one hour, will be configurable soon) to the default
calendar

::

    khal new 25.10. 16:00 18:00 Another Event :: with Alice and Bob

adds a new event on 25th of October lasting from 16:00 to 18:00 with additional description

::

    khal new 26.07. Great Event

adds a new all day event on 26.07.

``khal new`` should understand the following syntax:

::

    khal new startdatetime [enddatetime] description

where start- and enddatetime are either datetimes or times in the formats defined
in the config file. Start- and enddatetime can be one of the following:

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

At the moment default length is either 1h or 1 day (should be configurable soon,
too).


ikhal
-----
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



Notes on Timezones
-------------------
Getting localized time right, seems to be the most difficult part about
calendaring (and messing it up ends in missing the one imported meeting of the
week). So I'll briefly describe here, how khal tries to handle timezone
information, which information it can handle and which it can't.

All datetimes are saved to the local database as UTC Time. Datetimes that are
already UTC Time, e.g. ``19980119T070000Z`` are saved as such. Datetimes in
local time and with a time zone reference that khal can understand (Olson
database) are converted to UTC and than saved, e.g.
``TZID=America/New_York:19980119T020000``.  Floating times, e.g.
``19980118T230000`` (datetimes which are neither UTC nor have a timezone
specified) are treated as if the *default timezone* (specified in khal's config
file) was specified. Datetimes with a specified timezone that khal does not
understand are treated as if they were floating time.

khal expects you want *all* start and end dates displayed in *local time*
(which can be configured in the config file).

``VTIMEZONE`` components of calendars are totally ignored at the moment, as are
daylight saving times, instead it assumes that the TZID of DTSTART and DTEND
properties are valid OlsonDB values, e.g. America/New_York (seems to be the
default for at least the calendar applications I tend to use).

To summarize: as long as you are always in the same timezone and your calendar
is, too, khal probably shows the right start and end times. Otherwise: Good
Luck!

Seriously: be careful when changing timezones and do check if khal shows the
correct times anyway (and please report back if it doesn't).

Standards Compliance
--------------------
*khal* tries to follow standards and RFCs whereever possible. Known intentional
and unintentional deviations are listed here:


Events with neither END nor DURATION
************************************
While the RFC states
   A calendar entry with a "DTSTART" property but no "DTEND"
   property does not take up any time. It is intended to represent
   an event that is associated with a given calendar date and time
   of day, such as an anniversary. Since the event does not take up
   any time, it MUST NOT be used to record busy time no matter what
   the value for the "TRANSP" property.

khal transforms those events into all-day events lasting for one day (the start
date). As long a those events do not get edited, these changes will not be
written to the vdir (and with that to the CalDAV server). Any timezone
information that was associated with the start date gets discarded.

Miscellaneous
-------------
*khal* is written in python using, among others, icalendar_, dateutil_ and
pysqlite_. *khal* is open source and free software, released under the Expat/MIT
license.

.. _pysqlite: http://code.google.com/p/pysqlite/
.. _icalendar: https://github.com/collective/icalendar
.. _dateutil: http://labix.org/python-dateutil


License
-------
khal is released under the Expat/MIT License::

    Copyright (c) 2013-2014 Christian Geier and contributors

    Permission is hereby granted, free of charge, to any person obtaining a copy of
    this software and associated documentation files (the "Software"), to deal in
    the Software without restriction, including without limitation the rights to
    use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
    the Software, and to permit persons to whom the Software is furnished to do so,
    subject to the following conditions:

    The above copyright notice and this permission notice shall be included in all
    copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
    FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
    COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
    IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
    CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
