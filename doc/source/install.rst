Installing
==========

If khal is packaged for your OS/distribution, using your system's
standard package manager is probably the easiest way to install khal:

- pkgsrc_
- Fedora:
  - Fedora 22 and later::

      sudo dnf install -y khal

- Personal repos for openSUSE:

  - openSUSE 13.1::

      sudo zypper ar -f http://download.opensuse.org/repositories/home:/seilerphilipp/openSUSE_13.1/home_seilerphilipp

  - openSUSE 13.2::

      sudo zypper ar -f http://download.opensuse.org/repositories/home:/seilerphilipp/openSUSE_13.2/home_seilerphilipp

- AUR packages for ArchLinux: stable_ and development_ version.

.. _pkgsrc: http://pkgsrc.se/wip/khal-git
.. _stable: https://aur.archlinux.org/packages/khal/
.. _development: https://aur.archlinux.org/packages/khal-git/

If a package isn't available (or it is outdated) you need to fall back to one
of the methods mentioned below.

Install via Python's Package Managers
-------------------------------------

Since *khal* is written in python, you can use one of the package managers
available to install python packages, e.g. *pip*.

You can install the latest released version of *khal* by executing::

    pip install khal

or the latest development version by executing::

     pip install git+git://github.com/geier/khal.git

This should also take care of installing all required dependencies.


.. _requirements:

Requirements
------------

*khal* is written in python and can run on Python 2.7 and 3.3+. It requires a
Python with ``sqlite3`` support enabled (which is usually the case).

If you are installing python via *pip* or from source, be aware that since
*khal* indirectly depends on lxml_ you need to either install it via your
system's package manager or have python's libxml2's and libxslt1's headers
(included in a separate "development package" on some distributions) installed.

.. _icalendar: https://github.com/collective/icalendar
.. _vdirsyncer: https://github.com/untitaker/vdirsyncer
.. _lxml: http://lxml.de/
