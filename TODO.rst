TODO
====

* exceptions to recurrent events
* use a writable calendar for as a default calendar
* make read-only calendars static

* khal default ui:
  * show which calendar/resource an events belongs to

* ikhal:
  * new weeks should be loaded into the walker
  * make it look prettier
  * edit recurrence rules
  * do not loose chosen day highlight when focussing on Event Column
  * warning on pressing 'esc' in event editor when event has changed (including
    options to save and discard edit)



DONE
====
* [BUG] no exceptions on bad input in start or end dates
* exception on pressing save and cancel
* [BUG] moving cursor left in vcard editor does not work
* ikhal: editable events
* detect remotely deleted events
* while ikhal shows today focused, today's events are not shown
* events should be sorted
* khal should show tomorrows events, too
* ikhal should start with today focused
* output times are NOT localized yet
* events that continue over 00:00 get displayed to start on both days
  (confusing)
* recurrent events don't know their real start and end dates
* colored events (by icalendar)
* ikhal:
  * help text
  * new event on pressing n in calendar
  * reload EventList after editing or adding an event
  * show which resource/calendar an event belongs to and make it editable
  * prevent user from leaving EventEditor by pressing left or top (at least when event has been modified)

        * layout should probably be::
        ------------------------------------------
        |           |                            |
        | calendar  |                            |
        |           |   list of events           |
        |           |                            |
        |           |----------------------------|
        |           |                            |
        |           | currently selected event   |
        |           |                            |
        |           |                            |
        |           |                            |
        |           |                            |
        |           |                            |
        |           |                            |
        -------------------------------------------
