khal v0.4.0 released
====================

.. feed-entry::
        :date: 2015-02-02

A new release of khal is here: `khal v0.4.0`__ (also available on pypi_).

__ https://lostpackets.de/khal/downloads/khal-0.4.0.tar.gz

This release offers several functional improvements like better support for
recurring events or a major speedup when creating the caching database and some
new features like week number support or creating recurring events with `khal
new --repeat`.

Note to users
-------------

khal now requires click_ instead of docopt_ and, as usual, the local database
will need to be deleted.

For a more detailed list of changes, please have a look at the :ref:`changelog`.

.. _click: http://click.pocoo.org/
.. _docopt: http://docopt.org/
.. _pypi: https://pypi.python.org/pypi/khal/
