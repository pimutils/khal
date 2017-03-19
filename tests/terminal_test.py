from khal.terminal import merge_columns, colored


def test_colored():
    assert colored('test', 'light cyan') == '\33[1;36mtest\x1b[0m'
    assert colored('täst', 'white') == '\33[37mtäst\x1b[0m'
    assert colored('täst', 'white', 'dark green') == '\x1b[37m\x1b[42mtäst\x1b[0m'
    assert colored('täst', 'light magenta', 'dark green', True) == '\x1b[1;35m\x1b[42mtäst\x1b[0m'
    assert colored('täst', 'light magenta', 'dark green', False) == '\x1b[95m\x1b[42mtäst\x1b[0m'
    assert colored('täst', 'light magenta', 'light green', True) == '\x1b[1;35m\x1b[42mtäst\x1b[0m'
    assert colored('täst', 'light magenta', 'light green', False) == '\x1b[95m\x1b[102mtäst\x1b[0m'
    assert colored('täst', '5', '20') == '\x1b[38;5;5m\x1b[48;5;20mtäst\x1b[0m'
    assert colored('täst', '#F0F', '#00AABB') == \
        '\x1b[38;2;255;0;255m\x1b[48;2;0;170;187mtäst\x1b[0m'


class TestMergeColumns:

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
