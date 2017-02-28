#!/usr/bin/env python3
from setuptools import setup
import sys

if sys.version_info < (3, 3):
    errstr = "khal only supports python version 3.3+. Please Upgrade.\n"
    sys.stderr.write("#" * len(errstr) + '\n')
    sys.stderr.write(errstr)
    sys.stderr.write("#" * len(errstr) + '\n')
    sys.exit(1)

requirements = [
    'click>=3.2',
    'icalendar',
    'urwid',
    'pyxdg',
    'pytz',
    'python-dateutil',
    'configobj',
    # https://github.com/untitaker/python-atomicwrites/commit/4d12f23227b6a944ab1d99c507a69fdbc7c9ed6d  # noqa
    'atomicwrites>=0.1.7',
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
    description='A standards based terminal calendar',
    long_description=open('README.rst').read(),
    author='Christian Geier et. al.',
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
            'ikhal = khal.cli:main_ikhal',
        ]
    },
    install_requires=requirements,
    extras_require=extra_requirements,
    tests_require=test_requirements,
    setup_requires=['setuptools_scm != 1.12.0'],  # not needed when using packages from PyPI
    use_scm_version={'write_to': 'khal/version.py'},
    zip_safe=False,  # because of configobj loading the .spec file
    classifiers=[
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: MIT License",
        "Environment :: Console :: Curses",
        "Intended Audience :: End Users/Desktop",
        "Operating System :: POSIX",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: Utilities",
        "Topic :: Communications",
    ],
)
