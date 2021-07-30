khal v0.8.4 released
====================

.. feed-entry::
        :date: 2016-10-06

`khal v0.8.4`_ (pypi_) is a bugfix release that fixes a **critical bug** in `khal
import`. **All users are advised to upgrade as soon as possible**.

Details
~~~~~~~
If importing events from `.ics` files, any VTIMEZONEs (specifications of the
timezone) would *not* be imported with those events.
As khal understands Olson DB timezone specifiers (such as "Europe/Berlin" or
"America/New_York", events using those timezones are displayed in the correct
timezone, but all other events are displayed as if they were in the configured
*default timezone*.
**This can lead to imported events being shown at wrong times!**


Solution
~~~~~~~~
First, please upgrade khal to either v0.8.4 or, if you are using a version of khal directly
from the git repository, upgrade to the latest version from github_.

To see if you are affected by this bug, delete your local khal caching db,
(usually `~/.local/share/khal/khal.db`), re-run khal and watch out for lines
looking like this:
``warning: $PROPERTY has invalid or incomprehensible timezone information in
$long_uid.ics in $my_collection``.
You will then need to edit these files by hand and either replace the timezone
identifiers with the corresponding one from the Olson DB (e.g., change
`Europe_Berlin` to `Europe/Berlin`) or copy original VTIMZONE definition in.

If you have any problems with this, please either open an `issue at github`_ or come into
our `irc channel`_ (`#pimutils` on Libera.Chat).

We are sorry for any inconveniences this is causing you!


.. _khal v0.8.4: https://lostpackets.de/khal/downloads/khal-0.8.4.tar.gz
.. _github: https://github.com/pimutils/khal/
.. _issue at github: https://github.com/pimutils/khal/issues
.. _pypi: https://pypi.python.org/pypi/khal/
.. _irc channel: irc://#pimutils@Libera.Chat
