#!/usr/bin/env python2

import os
import string
import subprocess
import sys
import warnings

#from distutils.core import setup
from setuptools import setup

MAJOR = 0
MINOR = 1
PATCH = 1

RELEASE = True

VERSION = "{0}.{1}.{2}".format(MAJOR, MINOR, PATCH)

if not RELEASE:
    try:
        try:
            pipe = subprocess.Popen(["git", "describe", "--dirty", "--tags"],
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
    'lxml',
    'requests',
    'urwid',
    'pyxdg',
    'icalendar'
]
if sys.version_info[:2] in ((2, 6),):
    # there is no argparse in python2.6
    requirements.append('argparse')


extra_requirements = {
    'proctitle': ['setproctitle'],
    'keychain': ['keyring']
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
    packages=['khal', 'khal/ui'],
    scripts=['bin/khal', 'bin/ikhal'],
    requires=requirements,
    extras_require=extra_requirements,
    classifiers=[
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: MIT License",
        "Environment :: Console :: Curses",
        "Intended Audience :: End Users/Desktop",
        "Operating System :: POSIX",
        "Programming Language :: Python :: 2 :: Only",
        "Topic :: Utilities",
        "Topic :: Office/Business :: Scheduling"
    ],
)
