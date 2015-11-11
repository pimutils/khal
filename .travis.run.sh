#!/bin/sh
set -e

if [ "$BUILD" = "style" ]; then
    TOXENV=style
else
    TOXENV=$(echo py$TRAVIS_PYTHON_VERSION | tr -d . | sed -e 's/pypypy/pypy/') 
fi

tox -e $TOXENV
tox -e negtz
