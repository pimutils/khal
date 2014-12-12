
import pytest
import pytz

from khal.khalendar import backend
from khal.khalendar.exceptions import OutdatedDbVersionError

berlin = pytz.timezone('Europe/Berlin')


def test_new_db_version():
    dbi = backend.SQLiteDb('home', ':memory:', 'berlin', 'berlin')
    backend.DB_VERSION += 1
    with pytest.raises(OutdatedDbVersionError):
        dbi._check_table_version()

event_rrule_recurrence_id = """
BEGIN:VCALENDAR
BEGIN:VEVENT
UID:event_rrule_recurrence_id
SUMMARY:Arbeit
RRULE:FREQ=WEEKLY;UNTIL=20140725T053000Z
EXDATE:20140721T053000Z
DTSTART;TZID=Europe/Berlin:20140630T073000
DURATION:PT4H30M
END:VEVENT
BEGIN:VEVENT
UID:event_rrule_recurrence_id
SUMMARY:Arbeit
RECURRENCE-ID:20140707T053000Z
DTSTART;TZID=Europe/Berlin:20140707T073000
DTEND;TZID=Europe/Berlin:20140707T120000
END:VEVENT
END:VCALENDAR
"""


def test_event_rrule_recurrence_id():
    dbi = backend.SQLiteDb('home', ':memory:', 'berlin', 'berlin')
    assert dbi
