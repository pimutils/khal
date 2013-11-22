TODO
====

* exceptions to recurrent events

* ikhal:
  * new weeks should be loaded into the walker
  * make it look prettier
  * new event on pressing n in calendar
  * help text
  * [BUG] no exceptions on bad input in start or end dates
  * edit recurrence rules
  * show which resource an event belongs to and make it editable
  * prevent user from leaving EventEditor by pressing left or top (at least when event has been modified)
  * edit recurrence rules
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

DONE
====
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
