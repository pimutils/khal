Frequently Asked Questions (FAQ)
================================

* **start up of khal and ikhal is very slow**
      In some case the pytz (python timezone) is only available as a zip file,
      as pytz accesses several parts during initialization this takes some
      time. If `time python -c "import pytz; pytz.timezone('Europe/Berlin')"`
      takes nearly as much time as running khal, uncompressing that file via
      pytz via `(sudo) pip unzip pytz` might help.

* **ikhal raises an Exception: AttributeError: 'module' object has no attribute 'SimpleFocusListWalker'**
        You probably need to upgrade urwid to version 1.1.0, if your OS does come with
        an older version of *urwid* you can install the latest version to userspace
        (with out messing up your default installation) with `pip install --upgrade urwid --user`.


* **Installation stops with an error: source/str_util.c:25:20: fatal error: Python.h: No such file or directory**
        You do not have the Python development headers installed, on Debian based
        Distributions you can install them via *aptitude install python-dev*.

