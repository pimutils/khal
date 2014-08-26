khal
====
.. image:: https://travis-ci.org/geier/khal.svg?branch=master
    :target: https://travis-ci.org/geier/khal

*Khal* is a standards based CLI (console) calendar program. CalDAV_
compatibility is achieved by using vdir_/vdirsyncer_ as a backend, `allowing
syncing of calendars with a variety of other programs on a host of different
platforms`__.

*khal* is currently in an early stage of development, has a limited feature set
and is probably full of bugs. If you do try it out please report back any bugs
you might encounter.

.. image:: http://lostpackets.de/images/khal.png

Features
--------
(or rather: limitations)

- khal can read and write events/icalendars to vdir_
- fast and easy way to add new events
- ikhal (interactive khal) lets you browse and edit calendars and events
- support for recurring events is not complete yet, they cannot be deleted or
  edited and some recursion patterns are not understood yet
- you cannot edit the timezones of events
- khal should run on all major
  operating systems [1]_ (has been tested on FreeBSD and Debian GNU/Linux)


.. [1] except for Microsoft Windows

Feedback
--------
Please do provide feedback if *khal* works for you or even more importantly if
it doesn't. The preferred way to get in contact (especially if something isn't
working) is via github, otherwise you can reach me (the original author via
email at khal (at) lostpackets (dot) de , by jabber/XMPP at geier (at) jabber
(dot) ccc (dot) de.

.. _vdir: https://github.com/untitaker/vdir
.. _vdirsyncer: https://github.com/untitaker/vdirsyncer
.. _CalDAV: http://en.wikipedia.org/wiki/CalDAV
.. _github: https://github.com/geier/khal/
.. __: http://en.wikipedia.org/wiki/Comparison_of_CalDAV_and_CardDAV_implementations


Documentation
-------------
For khal's documentation have a look at the website_ or readthedocs_.

.. _website: https://lostpackets.de/khal/
.. _readthedocs: http://khal.readthedocs.org/

License
-------
khal is released under the Expat/MIT License::

    Copyright (c) 2013-2014 Christian Geier et al.

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
