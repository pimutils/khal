khal
====

Khal is a calendar program for the terminal for viewing, adding and editing
events and calendars. Khal is build on the iCalendar_ and vdir_ (allowing the
use of vdirsyncer_ for CalDAV_ compatibility) standards.


.. image:: http://lostpackets.de/images/khal.png

Features
--------
(or rather: limitations)

- khal can read and write events/icalendars to vdir_
- fast and easy way to add new events
- ikhal (interactive khal) lets you browse and edit calendars and events
- recurring events cannot be deleted (neither single instances nor the whole
  event)
- you cannot edit the timezones of events
- khal should run on all major
  operating systems [1]_ (has been tested on FreeBSD and Debian GNU/Linux)

.. [1] except for Microsoft Windows


.. _iCalendar: http://tools.ietf.org/html/rfc5546
.. _vdir: https://vdirsyncer.readthedocs.org/en/latest/vdir.html
.. _vdirsyncer: https://github.com/untitaker/vdirsyncer
.. _CalDAV: http://tools.ietf.org/html/rfc4791
.. __: http://en.wikipedia.org/wiki/Comparison_of_CalDAV_and_CardDAV_implementations


Table of Contents
=================

.. toctree::
   :maxdepth: 1

   install
   configure
   usage
   standards
   timezones
   contributing
   changelog
   faq
   license
   news
