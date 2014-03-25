Installation
------------
You can install *khal* from source by executing *python setup.py install*.

Copy and edit the supplied khal.conf.sample file (default location is
~/.config/khal/khal.conf).

Make sure you have sqlite3 (normally available by default), icalendar_, requests
(>0.10), urwid (>0.9) and pyxdg installed. Users of python 2.6 will also need to
install argparse.

khal has so far been successfully tested on recent versions of FreeBSD,
NetBSD, Debian and Ubuntu with python 2.6 and 2.7.

.. _keychain: https://pypi.python.org/pypi/keyring
.. _icalendar: https://github.com/collective/icalendar

