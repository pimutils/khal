Timezones
=========
Getting localized time right, seems to be the most difficult part about
calendaring (and messing it up ends in missing the one important meeting of the
week). So I'll briefly describe here, how khal tries to handle timezone
information, which information it can handle and which it can't.

In general, there are two different type of events. *Localized events* (with
*localized* start and end datetimes) which have timezone information attached to
their start and end datetimes, and *floating* events (with *floating* start and end
datetimes), which have no timezone information attached (all-day events, events that
last for complete days are floating as well). Localized events are always
observed at the same UTC_ (no matter what time zone the observer is in), but
different local times. On the other hand, floating events are always observed at
the same local time, which might be different in UTC.

In khal all localized datetimes are saved to the local database as UTC.
Datetimes that are already UTC, e.g. ``19980119T070000Z``, are saved as such,
others are converted to UTC (but don't worry, the timezone information does not
get lost). Floating events get saved in floating time, independently of the
localized events.

If you want to look up which events take place at a specified datetime, khal
always expects that you want to know what events take place at that *local*
datetime. Therefore, the datetime you asked for gets converted to UTC, the
appropriate *localized* events get selected and presented with their start and
end datetimes *converted* to *your local datetime*. For floating events no
conversion is necessary.

Khal (i.e. icalendar_) can understand all timezone identifiers as used in the
`Olson DB`_ and custom timezone definitions, if those VTIMEZONE components are
placed before the VEVENTS that make use of them (as most calendar programs seem
to do). In case a unknown (or unsupported) timezone is found, khal will assume
you want that event to be placed in the *default timezone* (which can be
configured in the configuration file as well).

khal expects you *always* want *all* start and end datetimes displayed in
*local time* (which can be set in the configuration file as well, otherwise
your computer's timezone is used).

.. _Olson DB: https://en.wikipedia.org/wiki/Tz_database
.. _UTC: https://en.wikipedia.org/wiki/Coordinated_Universal_Time
.. _icalendar: https://github.com/collective/icalendar
