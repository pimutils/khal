FAQ
===

Frequently asked questions:

* **Installation stops with an error: source/str_util.c:25:20: fatal error: Python.h: No such file or directory**
        You do not have the Python development headers installed, on Debian based
        Distributions you can install them via *aptitude install python-dev*.

* **unknown key "default_command"**
         This key was deprecated by f8d9135.
         See https://github.com/pimutils/khal/issues/648 for the rationale behind this removal.

.. _unmatched-exdates:

Why does khal warn about unmatched exclusions in a recurring event?
-------------------------------------------------------------------

A calendar file uses ``EXDATE`` to skip individual occurrences of a recurring
event. khal applies these exclusions after expanding the repeat rule (``RRULE``)
and adding any extra dates (``RDATE``). If an exclusion matches none of the
remaining occurrences khal has calculated, khal ignores it and applies the others.

For example, a meeting that starts on Thursday 4 September 2025 and repeats
every Thursday has no meetings in June 2025 to skip. A calendar app may have kept
those exclusions after the start of the series changed. Listing the same
exclusion twice can also trigger the warning.

If the schedule looks wrong, check the series start, repeat rule and excluded
dates in the calendar where you edit the event. The warning names the file and
shows the first unmatched date. At ``-v DEBUG`` verbosity, khal logs each
unmatched date when it reads the event into its database.
