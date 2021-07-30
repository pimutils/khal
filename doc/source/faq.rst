FAQ
===

Frequently asked questions:

* **Installation stops with an error: source/str_util.c:25:20: fatal error: Python.h: No such file or directory**
        You do not have the Python development headers installed, on Debian based
        Distributions you can install them via *aptitude install python-dev*.

* **unknown key "default_command"**
         This key was deprecated by f8d9135.
         See https://github.com/pimutils/khal/issues/648 for the rationale behind this removal.
