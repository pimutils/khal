khal
====

Khal is a CalDAV_ based calendar programm, `allowing syncing of calendars with a
variety of other programs on a host of different platforms`__.

*khal* is currently in a very early stage of development and has a very limited
feature set and is probably full of bugs.

Features
--------
(or rather: limitations)

- khal --sync syncs the all events in the next 365 days
- ikhal can show events in the current and next two months
- no recurring events support whatsoever
- no proper timezone support yet

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
