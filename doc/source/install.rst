Installation
============

If khal is packaged for your OS/distribution, using your system's
standard package manager is probably the easiest way to install khal.
khal has been packaged for, among others: Arch Linux (stable_ and development_
versions), Debian_, Fedora_, FreeBSD_, Guix_, and pkgsrc_.

.. _stable: https://aur.archlinux.org/packages/khal/
.. _development: https://aur.archlinux.org/packages/khal-git/
.. _Debian: https://packages.debian.org/search?keywords=khal&searchon=names
.. _Fedora: https://admin.fedoraproject.org/pkgdb/package/rpms/khal/
.. _FreeBSD: https://www.freshports.org/deskutils/py-khal/
.. _Guix: http://www.gnu.org/software/guix/packages/
.. _pkgsrc: http://pkgsrc.se/wip/khal-git

If a package isn't available (or it is outdated) you need to fall back to one
of the methods mentioned below.

Install via Python's Package Managers
-------------------------------------

Since *khal* is written in python, you can use one of the package managers
available to install python packages, e.g. *pip*.

You can install the latest released version of *khal* by executing::

    pip install khal

or the latest development version by executing::

     pip install git+git://github.com/pimutils/khal.git

This should also take care of installing all required dependencies.

Otherwise you can always download the latest release from pypi_ and execute::

        python setup.py install

or better::

        pip install .

in the unpacked distribution folder.

Since version 0.8 *khal* does **only supports python 3**. If you have
python 2 and 3 installed in parallel you might need to use `pip3` instead of
`pip` and `python3` instead of `python`. In case your operating system cannot
deal with python 2 and 3 packages concurrently, we suggest installing *khal* in
a virtualenv_ (e.g. by using virtualenvwrapper_ or with the help of pipsi_) and
than starting khal from that virtual environment.

.. _pipsi: https://github.com/mitsuhiko/pipsi
.. _pypi: https://pypi.python.org/pypi/khal
.. _virtualenv: https://virtualenv.pypa.io
.. _virtualenvwrapper: http://virtualenvwrapper.readthedocs.org/

.. _requirements:

Requirements
------------

*khal* is written in python and can run on Python 3.3+. It requires a Python
with ``sqlite3`` support enabled (which is usually the case).

If you are installing python via *pip* or from source, be aware that since
*khal* indirectly depends on lxml_ you need to either install it via your
system's package manager or have python's libxml2's and libxslt1's headers
(included in a separate "development package" on some distributions) installed.

.. _icalendar: https://github.com/collective/icalendar
.. _vdirsyncer: https://github.com/untitaker/vdirsyncer
.. _lxml: http://lxml.de/
