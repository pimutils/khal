khal
====

Khal is a CalDAV_ based calendar programm, `allowing syncing of calendars with a
variety of other programs on a host of different platforms`__.

*khal* is currently in a very early stage of development and has a very limited
feature set and is probably full of bugs.

Features
--------
(or rather: limitations)

- khal can sync events from CalDAV calendar collections
- add new events to a calendar (doesn't get uploaded just yet)
- ikhal can show events in the current and next two months
- no recurring events support whatsoever
- no proper timezone support yet
- is pretty Euro centric, weeks start on Mondays, khal uses a 24 hour clock and
  the default time zone is 'Europe/Berlin' (hopefully all of this will be
  configurable soon)


Usage
-----

**syncing**

 khal --sync

syncs the all events in the next 365 days

**quick event adding**

  khal --new 18:00 Awesome Event

adds a new event starting today at 18:00 with summary 'awesome event' (lasting
for the default time of one hour, will be configurable soon) to the default
calendar

  khal --new 25.10. 16:00 18:00 Another Event

adds a new event on 25th of October lasting from 16:00 to 18:00


  khal --new 26.07. Great Event

adds a new all day event on 26.07.

khal --new should be able to understand quite a range of dates, have a look at
the tests for more examples.

About
-----

*khal* is written in python using among others requests_, lxml_, icalendar_,
dateutil_ and pysqlite_. *khal* is open source and free software, released under
the Expat/MIT license.

.. __: http://en.wikipedia.org/wiki/Comparison_of_CalDAV_and_CardDAV_implementations
.. _CalDAV: http://en.wikipedia.org/wiki/CalDAV
.. _lxml: http://lxml.de/
.. _pysqlite: http://code.google.com/p/pysqlite/
.. _requests: http://python-requests.org
.. _icalendar: https://github.com/collective/icalendar
.. _dateutil: http://labix.org/python-dateutil
