#!/usr/bin/env python3
from setuptools import setup

requirements = [
    'click>=3.2',
    'icalendar',
    'urwid',
    'pyxdg',
    'pytz',
    'vdirsyncer',
    'python-dateutil',
    'configobj',
    'tzlocal>=1.0',
]

test_requirements = [
    'freezegun'
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
    tests_require=test_requirements,
    setup_requires=['setuptools_scm'],  # not needed when using packages from PyPI
    use_scm_version={'write_to': 'khal/version.py'},
    classifiers=[
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: MIT License",
        "Environment :: Console :: Curses",
        "Intended Audience :: End Users/Desktop",
        "Operating System :: POSIX",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: Utilities",
        "Topic :: Communications",
    ],
)
