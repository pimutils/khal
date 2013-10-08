Installation
------------
You can install *khal* from *pypi* via *pip install khal* or install it from
source by executing *python setup.py install*. 

Copy and edit the supplied khal.conf.sample file (default location is
~/.config/khal/khal.conf). If you don't want to store the password in clear
text in the config file, pyCardDAV will ask for it while syncing (and store it
in a keychain if keychain_ is installed).

Make sure you have sqlite3 (normally available by default), icalendar_, lxml(>2),
requests (>0.10), urwid (>0.9) and pyxdg installed. Users of python 2.6 will also
need to install argparse.

khal has so far been successfully tested on recent versions of FreeBSD,
NetBSD, Debian and Ubuntu with python 2.6 and 2.7 against davical, owncloud
and fruux.

.. _keychain: https://pypi.python.org/pypi/keyring
.. _icalendar: https://github.com/collective/icalendar

