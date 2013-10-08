Usage
-----
**install**

 python setup.py install

**configure**

copy *khal.conf.sample* to ~/.khal/khal.conf or ~/.config/khal/khal.conf and
edit to your liking

**syncing**

 khal --sync

syncs all events in the last month and next 365 days


**basic usage**

 khal

will show all events today and tomorrow

 ikhal

opens and interactive calendar browser, showing all events on the selected day


**quick event adding**

  khal --new 18:00 Awesome Event

adds a new event starting today at 18:00 with summary 'awesome event' (lasting
for the default time of one hour, will be configurable soon) to the default
calendar

  khal --new 25.10. 16:00 18:00 Another Event

adds a new event on 25th of October lasting from 16:00 to 18:00


  khal --new 26.07. Great Event

adds a new all day event on 26.07.

khal --new should be able to understand quite a range of dates, have a look at
the tests for more examples.


Write Support
-------------
To enable uploading events on the server, you need to enable write support.
Please note, that write support is experimental and please make sure you either
*really do have a backup* or only use it on test calendars.

To enable write support you need to put 

 write_support: YesPleaseIDoHaveABackupOfMyData

into every *Account* section you want to enable write support on in your config
file.


Notes on Timezones
-------------------
Getting localized time right, seems to be the most difficult part about
calendaring (and messing it up ends in missing the one imported meeting of the
week). So I'll briefly describe here, how khal tries to handle timezone
information, which information it can handle and wich it can't.

All datetimes are saved to the local database as UTC Time. Datetimes that are
already UTC Time, e.g. '19980119T070000Z' are saved as such. Datetimes in local
time and with a time zone reference that khal can understand (Olson database) are
converted to UTC and than saved, e.g. 'TZID=America/New_York:19980119T020000'.
Floating times, e.g. '19980118T230000' (datetimes which are neither UTC nor have a
timezone specified) are treated as if the *default timezone* (specified in
khal's config file) was specified. Datetimes with a specified timezone that
khal does not understand are treated as if they were floating time.

khal expects you want *all* start and end dates displayed in *local time* (which
can be configured in the config file).

*VTIMEZONE* components of calendars are totally ignored at the moment, as are
daylight saving times.

To summarize: as long as it is not daylight saving time, you are always in the
same timezone and your calendar is, too, khal probably shows the right start and
end times. Otherwise: Good Luck!

Seriously: be careful when changing timezones and do check if khal shows the
correct times anyway (and please report back if it doesn't).


