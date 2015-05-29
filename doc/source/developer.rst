Notes for developers
====================

If you want to hack on khal, the notes below might be of some interest to you.

iCalendar peculiarities
-----------------------

A single `.ics` can contain several VEVENTS, which might or might not be the
part of the same event. This can lead to issues with straight forward
implementations. Some of these, and the way khal is dealing with them, are
described below.

While one would expect every VEVENT to have its own unique UID (for what it's
worth they are named *unique identifier*), there is a case where several
VEVENTS have the same UID, but do describe the same (recurring) event.  In
this case, one VEVENT, containing an RRULE or RDATE element would be the
*proto* event, from which all recurrence instances are derived.  All other
VEVENTS with the same UID would then have a RECURRENCE-ID element (I'll call
them *child* event from now on) and describe deviations of at least one
recurrence instance (RECURRENCE-ID elements can also have the added property
RANGE=THISANDFUTURE, meaning the deviations described by this child event also
apply to all further recurrence instances.

Because it is possible that an event already in the database consists of a
master event and at least one child event gets updated and than consists only
of a master event, we currently *delete* all events with the same UID from the
database when inserting or updating a new event. But this means that we need
to update an event always at once (master and all child events) at the same
time (using `Calendar.update()` or `Calendar.new()` in this case)

As this wouldn't be bad enough, the standard looses no words on the ordering
on those VEVENTS in any given `.ics` file (at least I didn't find any). Not
only can the proto event be *behind* any or all RECURRENCE-ID events, but also
events with different UIDs can be in between.

We therefore currently first collect all events with the same UID and than
sort those by their type (proto or child), and the children by the value of the
RECURRENCE-ID property.
