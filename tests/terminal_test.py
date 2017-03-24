from khal.terminal import colored


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
