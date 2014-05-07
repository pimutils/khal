Frequently Asked Questions (FAQ)
================================


* **during sync an exception is raised: [Errno 185090050] _ssl.c:343: error:0B084002:x509 certificate routines:X509_load_cert_crl_file:system lib**
        khal cannot find the path to your certificate bundle, you need to supply it as a
        parameter to `ssl_verify` in your config file, e.g.
        `ssl_verify: /usr/share/ca-certificates/cacert.org/cacert.org_root.crt`.

* **ikhal raises an Exception: AttributeError: 'module' object has no attribute 'SimpleFocusListWalker'**
        You probably need to upgrade urwid to version 1.1.0, if your OS does come with
        an older version of *urwid* you can install the latest version to userspace
        (with out messing up your default installation) with `pip install --upgrade urwid --user`.


* **Installation stops with an error: source/str_util.c:25:20: fatal error: Python.h: No such file or directory**
        You do not have the Python development headers installed, on Debian based
        Distributions you can install them via *aptitude install python-dev*.

* **During sync an error occurs: TypeError: request() got an unexpected keyword argument 'verify'**
        You need to update your version of `requests`.

