#!/usr/bin/env python2
# vim: set ts=4 sw=4 expandtab sts=4 fileencoding=utf-8:

import os
import string
import subprocess
import warnings

from setuptools import setup

MAJOR = 0
MINOR = 4
PATCH = 0

RELEASE = False

VERSION = "{0}.{1}.{2}".format(MAJOR, MINOR, PATCH)

if not RELEASE:
    try:
        try:
            pipe = subprocess.Popen(
                ["git", "describe", "--always", "--dirty", "--tags"],
                stdout=subprocess.PIPE)
        except EnvironmentError:
            warnings.warn("WARNING: git not installed or failed to run")

        revision = pipe.communicate()[0].strip().lstrip('v')
        if pipe.returncode != 0:
            warnings.warn("WARNING: couldn't get git revision")

        if revision != VERSION:
            revision = revision.lstrip(string.digits + '.')
            VERSION += '.dev' + revision
    except:
        VERSION += '.dev'
        warnings.warn("WARNING: git not installed or failed to run")


def write_version():
    """writes the khal/version.py file"""
    template = """\
__version__ = '{0}'
"""
    filename = os.path.join(
        os.path.dirname(__file__), 'khal', 'version.py')
    with open(filename, 'w') as versionfile:
        versionfile.write(template.format(VERSION))
        print("wrote khal/version.py with version={0}".format(VERSION))

write_version()


requirements = [
    'click',
    'icalendar',
    'urwid',
    'pyxdg',
    'pytz',
    'vdirsyncer',
    'python-dateutil',
    'configobj',
    'tzlocal>=1.0',
]

extra_requirements = {
    'proctitle': ['setproctitle'],
}

setup(
    name='khal',
    version=VERSION,
    description='A CalDAV based calendar',
    long_description=open('README.rst').read(),
    author='Christian Geier',
    author_email='khal@lostpackets.de',
    url='http://lostpackets.de/khal/',
    license='Expat/MIT',
    packages=['khal', 'khal/ui', 'khal/khalendar', 'khal/settings'],
    package_data={'khal': [
        'settings/default.khal',
        'settings/khal.spec',
    ]},
    entry_points={
        'console_scripts': [
            'khal = khal.cli:main_khal',
            'ikhal = khal.cli:main_ikhal'
        ]
    },
    install_requires=requirements,
    extras_require=extra_requirements,
    classifiers=[
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: MIT License",
        "Environment :: Console :: Curses",
        "Intended Audience :: End Users/Desktop",
        "Operating System :: POSIX",
        "Programming Language :: Python :: 2 :: Only",
        "Topic :: Utilities",
        "Topic :: Communications",
    ],
)
