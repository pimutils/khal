Hacking
=======

.. note::

    All participants must follow the `pimutils Code of Conduct
    <http://pimutils.org/coc>`_.


**Please discuss your ideas with us, before investing a lot of time into
khal** (to make sure, no efforts are wasted).  Also if you have any questions on
khal's codebase, please don't hesitate to :ref:`contact <contact>` us, we will
gladly provide you with any information you need or set up a joined hacking
session.

The preferred way of submitting patches is via `github pull requests`_ (PRs). If you
are not comfortable with that, please :ref:`contact <contact>` us and we can
work out something else.  If you have something working, don't hesitate to open
a PR very early and ask for opinions.

Before we will accept your PR, we will ask you to:

 * add yourself to ``AUTHORS.txt`` if you haven't done it before
 * add a note to ``CHANGELOG.rst`` explaining your changes (if you changed
   anything user facing)
 * edit the documentation (again, only if your changes impact the way users
   interact with khal)
 * make sure all tests pass (see below)
 * write some tests covering your patch (this really is mandatory, unless it's
   in the urwid part, testing which is often difficult)
 * make sure your patch conforms with :pep:`008` (should be covered by passing
   tests)

Running the tests
-----------------
To run tests locally you can use tox_ to run khal's test suite with different
versions of python (run `tox` from a local khal repository), if this doesn't
work (or you only want to test against your current version of python) try
pytest_ and run `pytest tests` (the excecutable might be called `py.test`
depending on how you install it).  If you open a PR, `travis CI`_ will
automatically run the tests and report back in the PR thread on github.


.. _github: https://github.com/pimutils/khal/
.. _reported: https://github.com/pimutils/khal/issues?state=open
.. _issue: https://github.com/pimutils/khal/issues
.. _travis CI: https://travis-ci.org/pimutils/khal
.. _github pull requests: https://github.com/pimutils/khal/pulls
.. _tox: https://tox.readthedocs.org/
.. _pytest: http://pytest.org/


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
