khal v0.9.8 released with an IMPORTANT BUGFIX
=============================================

.. feed-entry::
        :date: 2017-10-05

`khal v0.9.8`_ comes with an **IMPORTANT BUGFIX**:
If editing an event in ikhal and not editing the end time but moving the cursor
through the end time field, the end time could be moved to the start time + 1
hour (the end *date* was not affected).


.. Warning::

  All users of khal are advised to **upgrade as soon as possible!**

Users of khal v0.9.3 and earlier are not affected.

Get `khal v0.9.8`_ from this site, or from pypi_.


.. _pypi: https://pypi.python.org/pypi/khal/
.. _khal v0.9.8: https://lostpackets.de/khal/downloads/khal-0.9.8.tar.gz
