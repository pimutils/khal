khal v0.2 released
==================

.. feed-entry::
        :date: 2014-06-27

A new release of khal is here: `khal v0.2.0`__ (also available on pypi_).

__ https://lostpackets.de/khal/downloads/khal-0.2.0.tar.gz


If you want to update your installation from pypi_, you can run `sudo pip
install --upgrade khal`.

From now on *khal* relies on vdirsyncer_ for CalDAV sync. While this makes
*khal* a bit more complicated to setup, *vdirsyncer* is much better tested than
*khal* and also the `bus factor`__ increased (at least for parts of the
project).

__ http://en.wikipedia.org/wiki/Bus_factor

You might want to head over to the tutorial_ on how to setup *vdirsyncer*.
Afterwards you will need to re-setup your *khal* configuration (copy the new
example config file), also you will need to delete your old (local) database, so
please make sure you did sync everything.

Also *khal*'s command line syntax changed qutie a bit, so you might want to head over the documentation_.

.. _pypi: https://pypi.python.org/pypi/khal/
.. _vdirsyncer: https://github.com/untitaker/vdirsyncer/
.. _tutorial: https://vdirsyncer.readthedocs.org/en/latest/tutorial.html
.. _documentation: http://lostpackets.de/khal/pages/usage.html
