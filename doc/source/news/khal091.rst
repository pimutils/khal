khal v0.9.1 released
====================

.. feed-entry::
        :date: 2017-01-25

This is a bug fix release for python 3.6.

Under python 3.6, datetimes with timezone information that is missing from the
icalendar file would be treated if they were in the system's local timezone, not
as if they were in khal's configured default timezone. This could therefore lead
to erroneous offsets in start and end times for those events.

To check if you are affected by this bug, delete khal's database file (usually
:file:`~/.local/share/khal/khal.db`), rerun khal and watch for error messages
that look like the one below:

   warning: DTSTART localized in invalid or incomprehensible timezone `FOO` in
   events/event_dt_local_missing_tz.ics. This could lead to this event being
   wrongly displayed.


All users (of python 3.6) are advised to upgrade as soon as possible.

Get `khal v0.9.1`__ from this site, or from pypi_.

__ https://lostpackets.de/khal/downloads/khal-0.9.1.tar.gz

.. _pypi: https://pypi.python.org/pypi/khal/
