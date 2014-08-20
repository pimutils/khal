Notes on Standard Compliance
============================

*khal* tries to follow standards and RFCs (most importantly :rfc:`5545`
*iCalendar*) whereever possible. Known intentional and unintentional deviations
are listed below.

Events with neither END nor DURATION
------------------------------------
While the RFC states
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
