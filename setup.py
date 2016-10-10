#!/usr/bin/env python
# vim: set ts=4 sw=4 expandtab sts=4 fileencoding=utf-8:

from setuptools import setup

requirements = [
    'click>=3.2',
    'icalendar',
    'urwid',
    'pyxdg',
    'pytz',
    'vdirsyncer<0.13',
    'python-dateutil',
    'configobj',
    'tzlocal>=1.0',
]

extra_requirements = {
    'proctitle': ['setproctitle'],
}

setup(
    name='khal',
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
    setup_requires=['setuptools_scm'],  # not needed when using packages from PyPI
    use_scm_version={'write_to': 'khal/version.py'},
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
