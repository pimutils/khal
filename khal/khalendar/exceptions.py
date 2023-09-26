# Copyright (c) 2013-2022 khal contributors
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from typing import Optional  # noqa

from ..exceptions import Error, FatalError, UnsupportedFeatureError


class UnsupportedRruleExceptionError(UnsupportedFeatureError):

    """we do not support exceptions that do not delete events yet"""

    def __init__(self, message='') -> None:
        x = 'This kind of recurrence exception is currently unsupported'
        if message:
            x += f': {message.strip()}'
        UnsupportedFeatureError.__init__(self, x)


class ReadOnlyCalendarError(Error):

    """this calendar is readonly and should not be modifiable from within
    khal"""


class EtagMissmatch(Error):

    """An event is trying to be modified from khal which has also been externally
    modified"""


class OutdatedDbVersionError(FatalError):

    """the db file has an older version and needs to be deleted"""


class CouldNotCreateDbDir(FatalError):

    """the db directory could not be created. Abort."""


class UpdateFailed(Error):

    """could not update the event in the database"""


class DuplicateUid(Error):

    """an event with this UID already exists"""
    existing_href = None  # type: Optional[str]


class NonUniqueUID(Error):

    """the .ics file contains more than one UID"""
