Timezones
=========
Getting localized time right, seems to be the most difficult part about
calendaring (and messing it up ends in missing the one imported meeting of the
week). So I'll briefly describe here, how khal tries to handle timezone
information, which information it can handle and which it can't.

All datetimes are saved to the local database as UTC Time. Datetimes that are
already UTC Time, e.g. ``19980119T070000Z`` are saved as such. Datetimes in
local time and with a time zone reference that khal can understand (Olson
database) are converted to UTC and than saved, e.g.
``TZID=America/New_York:19980119T020000``.  Floating times, e.g.
``19980118T230000`` (datetimes which are neither UTC nor have a timezone
specified) are treated as if the *default timezone* (specified in khal's
config file, or you computer's time zone is used) was specified. Datetimes
with a specified timezone that khal does not understand are treated as if they
were floating time.

khal expects you want *all* start and end dates displayed in *local time*
(which can be configured in the config file, otherwise your computer's
timezone is usued).

``VTIMEZONE`` components of calendars are understood, but *only* if they are
placed before the VEVENTS that use them (which every sensible calendar program
seems to do). Valid OlsonDB values (which most calendar applications use),
e.g. America/New_York are understood even if no ``VTIMEZONE`` component is
present.

To summarize: as long as you are always in the same timezone and your calendar
is, too, khal probably shows the right start and end times. Otherwise: Good
Luck!

Seriously: be careful when changing timezones and do check if khal shows the
correct times anyway (and please report back if it doesn't). As a safe measure
you might want to delete khal's database file after changing any timezone
setting, so that floating time
