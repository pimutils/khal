About
=====
*Khal* is a CLI (console), CalDAV_ based calendar program, `allowing syncing of
calendars with a variety of other programs on a host of different platforms`__.

*khal* is currently in a very early stage of development, has a very limited
feature set and is probably full of bugs. If you still want to take it out for a
spin, please know, that as long as you don't enable write support, there is no
chance at all that you might mess up your remote calendar. If you do try it out,
please report back any bugs you might encounter.

.. image:: http://lostpackets.de/images/khal.png

Features
--------
(or rather: limitations)

- khal can sync events from CalDAV calendar collections
- add simple new events to a calendar and upload them
- ikhal (interactive khal) can show events in the current and next two months
- simple recurring events support (no exceptions just yet)
- no proper timezone support yet
- is pretty Euro centric, weeks start on Mondays, khal uses a 24 hour clock and
  the default time zone is 'Europe/Berlin' (hopefully all of this will be
  configurable soon)
- khal should run on all major operating systems except for Microsoft's
  Windows; it has been tested on FreeBSD, NetBSD and Debian GNU/Linux.

.. __: http://en.wikipedia.org/wiki/Comparison_of_CalDAV_and_CardDAV_implementations
.. _CalDAV: http://en.wikipedia.org/wiki/CalDAV

