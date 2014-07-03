.. khal documentation master file, created by
   sphinx-quickstart on Fri Jul  4 00:00:47 2014.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

khal
====


*Khal* is a standards based CLI (console) calendar program. CalDAV_ compatibiliy
is achieved by using vdir_/vdirsyncer_ as a backend, `allowing syncing of
calendars with a variety of other programs on a host of different platforms`__.


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




Table of Contents
=================

.. toctree::
   :maxdepth: 1

   usage
   faq
   license



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

