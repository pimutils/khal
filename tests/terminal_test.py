# coding: utf-8
# vim: set ts=4 sw=4 expandtab sts=4:


import datetime

import pytest

from khal.calendar_display import vertical_month, getweeknumber, str_week
from khal.terminal import merge_columns, colored, bstring, rstring


def test_rstring():
    assert rstring('test') == '\x1b[7mtest\x1b[0m'
    assert rstring(u'täst') == u'\x1b[7mtäst\x1b[0m'


def test_bstring():
    assert bstring('test') == '\x1b[1mtest\x1b[0m'
    assert bstring(u'täst') == u'\x1b[1mtäst\x1b[0m'


def test_colored():
    assert colored('test', 'light cyan') == '\33[1;36mtest\x1b[0m'
    assert colored(u'täst', 'white') == u'\33[37mtäst\x1b[0m'



class TestMergeColumns(object):
    def test_longer_right(self):
        left = ['uiae', 'nrtd']
        right = ['123456', '234567', '345678']
        out = ['uiae    123456',
               'nrtd    234567',
               '        345678']
        assert merge_columns(left, right, width=4) == out

    def test_longer_left(self):
        left = ['uiae', 'nrtd', 'xvlc']
        right = ['123456', '234567']
        out = ['uiae    123456', 'nrtd    234567', 'xvlc    ']
        assert merge_columns(left, right, width=4) == out


    def test_wrapping_long_lines(self):
        left = ['    Mo Tu We Th Fr Sa Su ',
                'Apr 31  1  2  3  4  5  6 ',
                '     7  8  9 10 11 12 13 ']
        right = [
            '9:30 - 10:30 this is a super long and interesting event \
description, in fact it it is so long, that it wont fit on \
one line',
            '10:30 - 11:30 another long event description, while it isnt as \
intersting as the one before, it is even longer. Like a snake. \
A realllllllllllly long snake.']
        out = ['    Mo Tu We Th Fr Sa Su     9:30 - 10:30 this is a super long and interesting',
               'Apr 31  1  2  3  4  5  6     event description, in fact it it is so long, that',
               '     7  8  9 10 11 12 13     it wont fit on one line',
               '                             10:30 - 11:30 another long event description, while',
               '                             it isnt as intersting as the one before, it is even',
               '                             longer. Like a snake. A realllllllllllly long',
               '                             snake.']
        assert merge_columns(left, right, width=25) == out
