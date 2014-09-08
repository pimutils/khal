Changelog
=========
All notable changes to this project should be documented here.
For more detailed information have a look at the git log.

0.3.1
-----
released on 2014-09-08

* FIX: events deleted in the vdir are not shown anymore in khal. You might want
  to delete your local database file, if you have deleted any events on the
  server.
* FIX: in some cases non-ascii characters were printed even if unicode_symbols
  is set to False in the config
* FIX: events with different start and end timezones are now properly exported
  (the end timezone was disregarded when building an icalendar, but since
  timezones cannot be edited anyway, this shouldn't have caused any problems)
* FIX: calendars marked as read-only in the configuration file should now really
  be read-only

0.3.0
-----
released on 2014-09-03

* new unified documentation
    * html documentation (website) and man pages are all generated from the same
      sources via sphinx (type `make html` or `make man` in doc/, the result
      will be build in *build/html* or *build/man* respectively
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
