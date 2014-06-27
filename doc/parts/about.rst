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

