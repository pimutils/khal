Notes on Standard Compliance
============================

*khal* tries to follow standards and RFCs (most importantly :rfc:`5545`
*iCalendar*) where ever possible. Known intentional and unintentional deviations
are listed below.

Recurrent events with RDATE;VALUE=PERIOD
----------------------------------------

`RDATE` s with `PERIOD` values are currently not supported, as icalendar_ does
does not support it yet. Please submit any real world examples of events with
`RDATE;VALUE=PERIOD` you might encounter (khal will print warnings if you have
any in your calendars).

.. _icalendar: https://github.com/collective/icalendar/

Recurrent events with RANGE=THISANDPRIOR
----------------------------------------

Recurrent events with the `RANGE=THISANDPRIOR` are and will not be [1]_
supported by khal, as applications supporting the latest standard_ MUST NOT
create those. khal will print a warning if it encounters an event containing
`RANGE=THISANDPRIOR`.

.. [1] unless a lot of users request this feature

.. _standard: http://tools.ietf.org/html/rfc5546

Events with neither END nor DURATION
------------------------------------

While the RFC states::

   A calendar entry with a "DTSTART" property but no "DTEND"
   property does not take up any time. It is intended to represent
   an event that is associated with a given calendar date and time
   of day, such as an anniversary. Since the event does not take up
   any time, it MUST NOT be used to record busy time no matter what
   the value for the "TRANSP" property.

khal transforms those events into all-day events lasting for one day (the start
date). As long a those events do not get edited, these changes will not be
written to the vdir (and with that to the CalDAV server). Any timezone
information that was associated with the start date gets discarded.

.. note::
  While the main rationale for this behaviour was laziness on part of the main
  author of khal, other calendar software shows the same behaviour (e.g. Google
  Calendar and Evolution).
