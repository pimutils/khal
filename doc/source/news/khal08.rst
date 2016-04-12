khal v0.8.0 released
====================

.. feed-entry::
        :date: 2016-04-13

The latest version of khal has been released: `khal v0.8.0`__
(as always, also on pypi_).

__ https://lostpackets.de/khal/downloads/khal-0.8.0.tar.gz

We have recently dropped python 2 support, so this release is the first one that
only supports python 3 (3.3+).

There is one more backwards incompatible change:
The color `grey` has been renamed to `gray`, if you use it in your configuration
file, you will need to update to `gray`.

There are some new features that should be configuring khal easier, especially
for new users (e.g., new command `configure` helps with the initial
configuration). Also alarms can now be entered either when creating new events
with `new` or when editing them in ikhal.

Have a look at the changelog_ for more complete list of new features (of which
there are many).

.. _pypi: https://pypi.python.org/pypi/khal/
.. _changelog: changelog.html#id2
