# coding:utf-8

from khal.ui.widgets import delete_last_word


def test_delete_last_word():

    tests = [
        (u'Fü1ü  Bär!', u'Fü1ü  Bär', 1),
        (u'Füü Bär1', u'Füü ', 1),
        (u'Füü1 Bär1', u'Füü1 ', 1),
        (u' Füü Bär', u' Füü ', 1),
        (u'Füü Bär.Füü', u'Füü Bär.', 1),
        (u'Füü Bär.(Füü)', u'Füü Bär.(Füü', 1),
        (u'Füü ', u'', 1),
        (u'Füü  ', u'', 1),
        (u'Füü', u'', 1),
        (u'', u'', 1),

        (u'Füü Bär.(Füü)', u'Füü Bär.', 3),
        (u'Füü Bär1', u'', 2),
        (u'Lorem ipsum dolor sit amet, consetetur sadipscing elitr, '
         'sed diam nonumy eirmod tempor invidunt ut labore et dolore '
         'magna aliquyam erat, sed diam volest.',
         'Lorem ipsum dolor sit amet, consetetur sadipscing elitr, '
         'sed diam nonumy eirmod tempor invidunt ut labore ',
         10)
    ]

    for org, short, number in tests:
        assert delete_last_word(org, number) == short
