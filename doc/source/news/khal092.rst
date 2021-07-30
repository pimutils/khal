khal v0.9.2 released
====================

.. feed-entry::
        :date: 2017-02-13


This is an **important bug fix release**, that fixes a bunch of different bugs,
but most importantly:

 * if weekstart != 0 ikhal would show wrong weekday names
 * allday events added with `khal new DATE TIMEDELTA` (e.g., 2017-01-18 3d)
   were lasting one day too long

Special thanks to Tom Rushworth for finding and reporting both bugs!

All other fixed bugs would be rather obvious if you happened to run into them,
as they would lead to khal crashing in one way or another.

One new feature made its way into this release as well, which is good news for
all users pining for the way ikhal's right column behaved in pre 0.9.0 days:
setting new configuration option [view]dynamic_days=False, will make that column
behave similar as it used to.

.. Warning::

  All users of khal 0.9.x are advised to **upgrade as soon as possible**.

Users of khal 0.8.x are not affected by either bug.

Get `khal v0.9.2`__ from this site, or from pypi_.

__ https://lostpackets.de/khal/downloads/khal-0.9.2.tar.gz

.. _pypi: https://pypi.python.org/pypi/khal/
