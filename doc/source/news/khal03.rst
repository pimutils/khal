khal v0.3 released
==================

.. feed-entry::
        :date: 2014-09-03

A new release of khal is here: `khal v0.3.0`__ (also available on pypi_).

__ https://lostpackets.de/khal/downloads/khal-0.3.0.tar.gz


If you want to update your installation from pypi_, you can run `sudo pip
install --upgrade khal`.

CHANGELOG
---------
* new unified documentation
    * html documentation (website) and man pages are all generated from the same
      sources via sphinx (type `make html` or `make man` in doc/, the result
      will be build in *build/html* or *build/man* respectively (also available
      on `Read the Docs`__)
    * the new documentation lives in doc/
    * the package sphinxcontrib-newsfeed is needed for generating the html
      version (for generating an RSS feed)
    * the man pages live doc/build/man/, they can be build by running
      `make man` in doc/sphinx/
* new dependencies: configobj, tzlocal>=1.0
* **IMPORTANT**: the configuration file's syntax changed (again), have a look at the new
  documentation for details
* local_timezone and default_timezone will now be set to the timezone the
  computer is set to (if they are not set in the configuration file)

__ https://khal.readthedocs.org

.. _pypi: https://pypi.python.org/pypi/khal/
.. _vdirsyncer: https://github.com/pimutils/vdirsyncer/
