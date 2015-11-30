from khal.terminal import merge_columns, colored


def test_colored():
    assert colored('test', 'light cyan') == '\33[1;36mtest\x1b[0m'
    assert colored('täst', 'white') == '\33[37mtäst\x1b[0m'


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
