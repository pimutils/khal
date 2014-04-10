Usage
-----
**install**

::

    python setup.py install

**configure**

copy ``khal.conf.sample`` to ``~/.khal/khal.conf`` or
``~/.config/khal/khal.conf`` and edit to your liking.


**basic usage**

::

    khal

will show all events today and tomorrow

::

    ikhal

opens an interactive calendar browser, showing all events on the selected day.
See below for usage notes on ikhal.

**quick event adding**

::

    khal --new 18:00 Awesome Event

adds a new event starting today at 18:00 with summary 'awesome event' (lasting
for the default time of one hour, will be configurable soon) to the default
calendar

::

    khal --new 25.10. 16:00 18:00 Another Event :: with Alice and Bob

adds a new event on 25th of October lasting from 16:00 to 18:00 with additional description

::

    khal --new 26.07. Great Event

adds a new all day event on 26.07.

`khal --new` should understand the following syntax:

::

    khal --new startdatetime [enddatetime] description

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
information, which information it can handle and wich it can't.

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


