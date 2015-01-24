
import pytest
import pytz

from datetime import datetime

from khal.khalendar import backend
from khal.khalendar.exceptions import OutdatedDbVersionError

berlin = pytz.timezone('Europe/Berlin')
locale = {'local_timezone': berlin, 'default_timezone': berlin}


def test_new_db_version():
    dbi = backend.SQLiteDb('home', ':memory:', locale=locale)
    backend.DB_VERSION += 1
    with pytest.raises(OutdatedDbVersionError):
        dbi._check_table_version()

event_rrule_recurrence_id = """
BEGIN:VCALENDAR
BEGIN:VEVENT
UID:event_rrule_recurrence_id
SUMMARY:Arbeit
RRULE:FREQ=WEEKLY;COUNT=6
EXDATE:20140721T053000Z
DTSTART;TZID=Europe/Berlin:20140630T070000
DTEND;TZID=Europe/Berlin:20140707T120000
END:VEVENT
BEGIN:VEVENT
UID:event_rrule_recurrence_id
SUMMARY:Arbeit
RECURRENCE-ID:20140707T050000Z
DTSTART;TZID=Europe/Berlin:20140707T090000
DTEND;TZID=Europe/Berlin:20140707T140000
END:VEVENT
END:VCALENDAR
"""


def test_event_rrule_recurrence_id():
    dbi = backend.SQLiteDb('home', ':memory:', locale=locale)
    assert dbi.list() == list()
    events = dbi.get_time_range(datetime(2014, 6, 30, 0, 0), datetime(2014, 7, 26, 0, 0))
    assert events == list()
    dbi.update(event_rrule_recurrence_id, href='12345.ics', etag='abcd')
    assert dbi.list() == [('12345.ics', 'abcd')]
    events = dbi.get_time_range(datetime(2014, 4, 30, 0, 0), datetime(2014, 9, 26, 0, 0))
    events.sort(key=lambda x: x.start)
    assert len(events) == 6

    assert events[0].start == berlin.localize(datetime(2014, 6, 30, 7, 0))
    assert events[1].start == berlin.localize(datetime(2014, 7, 7, 9, 0))
    assert events[2].start == berlin.localize(datetime(2014, 7, 14, 7, 0))
    assert events[3].start == berlin.localize(datetime(2014, 7, 21, 7, 0))
    assert events[4].start == berlin.localize(datetime(2014, 7, 28, 7, 0))
    assert events[5].start == berlin.localize(datetime(2014, 8, 4, 7, 0))

    assert dbi
