Changelog
=========
All notable changes to this project should be documented here.
For more detailed information have a look at the git log.

0.3.0 - not released yet
------------------------
* new unified documentation
    * html documentation (website) and man pages are all generated from the same
      sources via sphinx (type `make html` or `make man` in doc/, the result
      will be build in *build/html* or *build/man* respectively
    * the new documentation lives in doc/
    * the package sphinxcontrib-newsfeed is needed for generating the html
      version (for generating an RSS feed)
    * the man pages live doc/build/man/, they can be build by running
      `make man` in doc/sphinx/
* new dependency: configobj
* **IMPORTANT**: the configuration file's syntax changed (again), have a look at the new
  documentation for details
