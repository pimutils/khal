import icalendar


class Event(object):
    def __init__(self, ical):
        self.vevent = icalendar.Event.from_ical(ical)

    @property
    def start(self):
        return self.vevent['DTSTART'].dt

    @property
    def end(self):
        try:
            return self.vevent['DTEND'].dt
        except:
            raise

    @property
    def summary(self):
        return self.vevent['SUMMARY']
