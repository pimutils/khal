Hacking
=======

.. note::

    All participants must follow the `pimutils Code of Conduct
    <http://pimutils.org/coc>`_.


**Please discuss your ideas with us, before investing a lot of time into
khal** (to make sure, no efforts are wasted).  Also, if you have any questions
on khal's codebase, please don't hesitate to :ref:`contact <contact>` us, we
will gladly provide you with any information you need or set up a joined
hacking session.

The preferred way of submitting patches is via `github pull requests`_ (PRs).  If you
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

Plugins
-------

Khal now supports plugins, currently for supporting new commands (`example
command plugin`_), formatting (`example formatting plugin`_), and
colors (`example color plugin`_).

If you want to develop a new feature, please check if it can be implemented as
a plugin.  If you are unsure, please ask us, we will gladly help you and, if
needed, also extend the plugin API.  We would like to see new functionality
matured in plugins before we consider integrating it into khal's core.

.. _`example command plugin`: https://github.com/geier/khal_navigate
.. _`example formatting plugin`: https://github.com/tcuthbert/khal/tree/plugin/example
.. _`example color plugin`: https://github.com/geier/khal_gruvbox/tree/importlib


Color scheme plugins
*********************

Khal color schemes plugins are only availlable for the `ikhal` interface. They
are installed as python packages (e.g. `python -m pip install khal_gruvbox`).
A color scheme plugin must provide an entry point `khal_colorscheme` and contain
an urwid palette definition. The palette definition is a list of tuples, where
each tuple contains an attribute name and a color definition.  See the `urwid
documentation`_ for more information. All currently avaialable attributes can be
found in `khal's source code`_.

.. _`urwid documentation`: http://urwid.org/manual/displayattributes.html
.. _`khal's source code`: https://github.com/pimutils/khal/blob/master/khal/ui/colors.py

General notes for developing khal (and lots of other python packages)
---------------------------------------------------------------------

The below notes are meant to be helpful if you are new to developing python
packages in general and/or khal specifically.  While some of these notes are
therefore specific to khal, most should apply to lots of other python packages
developed in comparable setup.  Please note that all commands (if not otherwise
noted) should be executed at the root of khal's source directory, i.e., the
directory you got by cloning khal via git.

Please note that fixes and enhancements to these notes are very welcome, too.

Isolation
*********
When working on khal (or for any other python package) it has proved very
beneficial to create a new *virtual environments* (with the help of
virtualenv_), to be able to run khal in isolation from your globally installed
python packages and to ensure to not run into any conflicts very different
python packages depend on different version of the same library.
virtualenvwrapper_ (for bash and zsh users) and virtualfish_ (for fish users)
are handy wrappers that make working with virtual environments very comfortable.

After you have created and activated a virtual environment, it is recommended to
install khal via :command:`pip install -e .` (from the base of khal's source
directory), this install khal in an editable development mode, where you do not
have to reinstall khal after every change you made, but where khal will always
have picked up all the latest changes (except for adding new files, hereafter
reinstalling khal *is* necessary).

Testing
*******
khal has an extensive self test suite, that lives in :file:`tests/`.
To run the test suite, install `pytest` and run :command:`py.test tests`, pytest
will then collect and run all tests and report on any failures (which you should
then proceed to fix).  If you only want to run tests contained in one file, run,
e.g., :command:`py.test tests/backend_test.py`.  If you only want to run one or
more specific tests, you can filter for them with :command:`py.test -k calendar`,
which would only run tests including `calendar` in their name.

To ensure that khal runs on all currently supported version of python, the self
test suite should also be run with all supported versions of python.  This can
locally be done with tox_.  After installing tox, running tox will create new
virtual environments (which it will reuse on later runs), one for each python
version specified in :file:`tox.ini`, run the test suite and report on it.

If you open a pull request (*PR*) on github, the continuous integration service
`GitHub Actions`_ will automatically perform exactly those tasks and then comment
on the success or failure.

If you make any non-trivial changes to khal, please ensure that those changes
are covered by (new) tests.  As testing :command:`ikhal` (the part of
:command:`khal` making use of urwid_) has proven rather complicated (as can be
seen in the lack tests covering that part of khal), automated testing of changes
of that part is therefore not mandatory, but very welcome nonetheless.

To make sure all major code paths are run through at least once, please check
the *coverage* the tests provide.  This can be done with pytest-cov_.  After
installing pytest-cov, running :command:`py.test --cov khal --cov-report=html
tests` will generate an html-based report on test coverage (which can be
found in :file:`htmlcov`), including a color-coded version of khal's source code,
indicating which lines have been run and which haven't.

Debugging
*********
For an improved debugging experience on the command line, `pdb++`_ is
recommended (install with :command:`pip install pdbpp`). :command:`pdb++` is a
drop in replacement for python's default debugger, and can therefore be used
like the default debugger, e.g., invoked by placing ``import pdb;
pdb.set_trace()`` at the respective place.  One of the main reasons for choosing
:command:`pdb++` over alternatives like IPython's debugger ipdb_, is that it
works nicely with :command:`pytest`, e.g., running `py.test --pdb tests` will
drop you at a :command:`pdb++` prompt at the place of the first failing test.

Documentation
*************
Khal's documentation, which is living in :file:`doc`, is using sphinx_ to
generate the html documentation as well as the man page from the same sources.
After install `sphinx` and `sphinxcontrib-newsfeed` you should be able to build
the documentation with :command:`make html` and :command:`make man` respectively
from the root of the :file:`doc` directory (note that this requires `GNU make`,
so on some system running :command:`gmake` may be required).

If you make any changes to how a user would interact with khal, please change or
add the relevant section(s) in the documentation, which uses the
reStructuredText_ format, which shouldn't be too hard to use after looking at
some of the existing documentation (even for users who never used it before).

Also, summarize your changes in :file:`CHANGELOG.rst`,  pointing readers to the
(updated) documentation is fine.

Code Style
**********
khal's source code should adhere to the rules laid out in :pep:`008`, except
for allowing line lengths of up to 100 characters if it improves
overall legibility (use your judgement).  This can be checked by installing and
running ruff_ (run with :command:`ruff` from khal's source directory), which
will also be run with tox and GitHub Actions, see section above.

We try to document the parameters functions and methods accept, including their
types, and their return values in the `sphinx style`_, though this is currently
not used thoroughly.

Note that we try to use double quotes for human readable strings, e.g., strings
that one would internationalize and single quotes for strings used as
identifiers, e.g., in dictionary keys::

    my_event['greeting'] = "Hello World!"

.. _github: https://github.com/pimutils/khal/
.. _reported: https://github.com/pimutils/khal/issues?state=open
.. _issue: https://github.com/pimutils/khal/issues
.. _GitHub Actions: https://github.com/pimutils/khal/actions/workflows/ci.yml
.. _github pull requests: https://github.com/pimutils/khal/pulls
.. _tox: https://tox.readthedocs.org/
.. _pytest: http://pytest.org/
.. _pytest-cov: https://pypi.python.org/pypi/pytest-cov
.. _ruff: https://github.com/charliermarsh/ruff
.. _sphinx: http://www.sphinx-doc.org
.. _restructuredtext: http://www.sphinx-doc.org/en/1.5.1/rest.html
.. _ipdb: https://pypi.python.org/pypi/ipdb
.. _pdb++: https://pypi.python.org/pypi/pdbpp/
.. _urwid: http://urwid.org/
.. _virtualenv: https://virtualenv.pypa.io/en/stable/
.. _virtualenvwrapper: https://virtualenvwrapper.readthedocs.io/
.. _virtualfish: https://github.com/adambrenecki/virtualfish



.. _sphinx style: http://www.sphinx-doc.org/en/1.5.1/domains.html#info-field-lists


iCalendar peculiarities
-----------------------
These notes are meant for people who want to deep dive into
:file:`khal.khalendar.backend.py` and are not recommended reading material for
anyone else.

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
master event and at least one child event gets updated and then consists only
of a master event, we currently *delete* all events with the same UID from the
database when inserting or updating a new event. But this means that we need
to update an event always at once (master and all child events) at the same
time (using `Calendar.update()` or `Calendar.new()` in this case)

As this wouldn't be bad enough, the standard looses no words on the ordering
on those VEVENTS in any given `.ics` file (at least I didn't find any). Not
only can the proto event be *behind* any or all RECURRENCE-ID events, but also
events with different UIDs can be in between.

We therefore currently first collect all events with the same UID and then
sort those by their type (proto or child), and the children by the value of the
RECURRENCE-ID property.
