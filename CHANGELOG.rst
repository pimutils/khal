Changelog
=========
All notable changes to this project will be documented here.
For more detailed information have a look at the git log.

0.3.0 - not released yet
------------------------
* new unified documentation
    * website, README and man pages are all generated from the same sources via
      sphinx
    * for now, the new documentation lives in doc/sphinx/, but will be moved to
      doc/ when the new website goes live
    * the package sphinxcontrib-newsfeed is needed for generating the html
      version (for generating an RSS feed)
    * the man pages live doc/sphinx/build/man/, they can be build by running
      `make man` in doc/sphinx/
* khal now uses configobj for reading the configuration, also the
  configuration file's syntax changed, have a look at the new documentation
  for details
