Feedback and Contributing
=========================

Feedback
--------
Please do provide feedback if *khal* works for you or even more importantly
if it doesn't. Feature requests and other ideas on how to improve khal are also
welcome.

In case you are not satisfied with khal, there are at least two other projects
with similar aims you might want to check out: calendar-cli_ (no
offline storage and a bit different scope) and gcalcli_ (only works with
google's calendar).

.. _calendar-cli: https://github.com/tobixen/calendar-cli
.. _gcalcli: https://github.com/insanum/gcalcli

Submitting a Bug
----------------
If you found a bug or any part of khal isn't working as you expected, please
check if that bug is also present in the latest version from github (see
:doc:`install`) and is not already reported_ (you still might want to comment on
an already open issue).

If it isn't, please open a new bug.  In case you submit a new bug please
include:

 * how you ran khal (please run in verbose mode with `-v`)
 * what you expected khal to do
 * what it did instead
 * everything khal printed to the screen (you may redact private details)
 * in case khal complains about a specific .ics file, please include that as
   well (or create a .ics which leads to the same error without any private
   information)
 * the version of khal and python you are using, which operating system you are
   using and how you installed khal

Suggesting Features
-------------------
If you believe khal is lacking a useful feature or some part of khal is not
working the way you think it should, please first check if there isn't already
a relevant issue_ for it and otherwise open a new one.

Hacking
-------
**Please discuss your ideas with us, before investing a lot of time into
khal** (to make sure, no efforts are wasted).  Also if you have any questions on
khal's codebase, please don't hesitate to :doc:`contact <contact>` us, we will
gladly provide you with any information you need or set up a joined hacking
session.

The preferred way of submitting patches is via `github pull requests`_ (PRs). If you
are not comfortable with that, please :doc:`contact <contact>` us and we can
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
*****************
To run tests locally you can use tox_ to run khal's test suite with different
versions of python (just run `tox` from a local khal repository).  If you open a
PR, `travis CI`_ will automatically run the test and report in the PR thread on
github.


.. _github: https://github.com/pimutils/khal/
.. _reported: https://github.com/pimutils/khal/issues?state=open
.. _issue: https://github.com/pimutils/khal/issues
.. _travis CI: https://travis-ci.org/pimutils/khal
.. _github pull requests: https://github.com/pimutils/khal/pulls
.. _tox: https://tox.readthedocs.org/
