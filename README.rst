khal
====
.. image:: https://travis-ci.org/pimutils/khal.svg?branch=master
    :target: https://travis-ci.org/pimutils/khal

.. image:: https://codecov.io/github/pimutils/khal/coverage.svg?branch=master
  :target: https://codecov.io/github/pimutils/khal?branch=master

*Khal* is a standards based CLI (console) calendar program, able to synchronize
with CalDAV_ servers through vdirsyncer_.

.. image:: http://lostpackets.de/images/khal.png

Features
--------
(or rather: limitations)

- khal can read and write events/icalendars to vdir_, so vdirsyncer_ can be
  used to `synchronize calendars with a variety of other programs`__, for
  example CalDAV_ servers.
- fast and easy way to add new events
- ikhal (interactive khal) lets you browse and edit calendars and events
- only rudimentary support for creating and editing recursion rules
- you cannot edit the timezones of events
- works with python 3.3+
- khal should run on all major operating systems [1]_

.. [1] except for Microsoft Windows

Feedback
--------
Please do provide feedback if *khal* works for you or even more importantly if
it doesn't. The preferred way to get in contact (especially if something isn't
working) is via github or IRC (#pimutils on Freenode), otherwise you can reach
the original author via email at khal (at) lostpackets (dot) de or via
jabber/XMPP at geier (at) jabber (dot) ccc (dot) de.

.. _vdir: https://vdirsyncer.readthedocs.org/en/stable/vdir.html
.. _vdirsyncer: https://github.com/pimutils/vdirsyncer
.. _CalDAV: http://en.wikipedia.org/wiki/CalDAV
.. _github: https://github.com/pimutils/khal/
.. __: http://en.wikipedia.org/wiki/Comparison_of_CalDAV_and_CardDAV_implementations


Documentation
-------------
For khal's documentation have a look at the website_ or readthedocs_.

.. _website: https://lostpackets.de/khal/
.. _readthedocs: http://khal.readthedocs.org/


Alternatives
------------
Projects with similar aims you might want to check out are calendar-cli_ (no
offline storage and a bit different scope) and gcalcli_ (only works with
google's calendar).

.. _calendar-cli: https://github.com/tobixen/calendar-cli
.. _gcalcli: https://github.com/insanum/gcalcli

Contributing
------------
You want to contribute to *khal*? Awesome!

The most appreciated way of contributing is by supplying code or documentation,
reporting bugs, creating packages for your favorite operating system, making
khal better know by telling your friends about it, etc. If you don't have
the time or the means to contribute in any of the above mentioned ways,
donations are appreciated, too.

.. image:: https://api.flattr.com/button/flattr-badge-large.png
   :alt: flattr button
   :target: http://flattr.com/thing/2475065/geierkhal-on-GitHub/

License
-------
khal is released under the Expat/MIT License::

    Copyright (c) 2013-2015 Christian Geier et al.

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
