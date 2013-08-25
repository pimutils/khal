khal
====

Khal is a CLI (console), CalDAV_ based calendar programm, `allowing syncing of calendars with a
variety of other programs on a host of different platforms`__.

*khal* is currently in a very early stage of development, has a very limited
feature set and is probably full of bugs. If you still want to take it out for a
spin, please know, that as long as you don't enable write support, there is no
chance at all that you might mess up your remote calendar. If you do try it out,
please report back any bugs you might encounter.

Features
--------
(or rather: limitations)

- khal can sync events from CalDAV calendar collections
- add simple new events to a calendar and upload them
- ikhal can show events in the current and next two months
- simple recurring events support (no exceptions just yet)
- no proper timezone support yet
- is pretty Euro centric, weeks start on Mondays, khal uses a 24 hour clock and
  the default time zone is 'Europe/Berlin' (hopefully all of this will be
  configurable soon)
- khal should run on all major operating systems [1]_ (has been tested on FreeBSD and
  Debian GNU/Linux)


.. [1] except for Microsoft Windows

Usage
-----

**install**

 python setup.py install

**configure**

copy *khal.conf.sample* to ~/.khal/khal.conf or ~/.config/khal/khal.conf and
edit to your liking

**syncing**

 khal --sync

syncs all events in the last month and next 365 days


**basic usage**

 khal

will show all events today and tomorrow

 ikhal

opens and interactive calendar browser, showing all events on the selected day


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


Write Support
-------------

To enable uploading events on the server, you need to enable write support.
Please note, that write support is experimental and please make sure you either
*really do have a backup* or only use it on test calendars.

To enable write support you need to put 

 write_support: YesPleaseIDoHaveABackupOfMyData

into every *Account* section you want to enable write support on in your config
file.

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
