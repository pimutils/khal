import icalendar


class Event(object):
    def __init__(self, ical, local_tz=None, default_tz=None):
        self.vevent = icalendar.Event.from_ical(ical)
        self.local_tz = local_tz
        self.default_tz = default_tz

    @property
    def start(self):
        start = self.vevent['DTSTART'].dt
        if start.tzinfo is None:
            start.astimezone(self.default_tz)
        start = start.astimezone(self.local_tz)
        return self.vevent['DTSTART'].dt

    @property
    def end(self):
        # TODO take care of events with no DTEND but DURATION and neither DTEND
        # nor DURATION
        end = self.vevent['DTEND'].dt
        if end.tzinfo is None:
            end.astimezone(self.default_tz)
        end = end.astimezone(self.local_tz)
        return end

    @property
    def summary(self):
        return self.vevent['SUMMARY']
