khal v0.3.1 released
====================

.. feed-entry::
        :date: 2014-09-08

A new release of khal is here: `khal v0.3.1`__ (also available on pypi_).

__ https://lostpackets.de/khal/downloads/khal-0.3.1.tar.gz


This is a bugfix release, bringing no new features. The last release suffered
from a major bug, where events deleted on the server (and in the vdir) were not
deleted in khal's caching database and therefore still displayed in khal.
Therefore, after updating please delete your local database.

For more information on other fixed bugs, see :ref:`changelog`.


.. _pypi: https://pypi.python.org/pypi/khal/
