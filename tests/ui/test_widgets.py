import pytest
import urwid

from khal.ui.widgets import (
    FocusLineBoxColor,
    FocusLineBoxTop,
    FocusLineBoxWidth,
    delete_last_word,
)


def test_delete_last_word():
    tests = [
        ("Fü1ü  Bär!", "Fü1ü  Bär", 1),
        ("Füü Bär1", "Füü ", 1),
        ("Füü1 Bär1", "Füü1 ", 1),
        (" Füü Bär", " Füü ", 1),
        ("Füü Bär.Füü", "Füü Bär.", 1),
        ("Füü Bär.(Füü)", "Füü Bär.(Füü", 1),
        ("Füü ", "", 1),
        ("Füü  ", "", 1),
        ("Füü", "", 1),
        ("", "", 1),
        ("Füü Bär.(Füü)", "Füü Bär.", 3),
        ("Füü Bär1", "", 2),
        (
            "Lorem ipsum dolor sit amet, consetetur sadipscing elitr, "
            "sed diam nonumy eirmod tempor invidunt ut labore et dolore "
            "magna aliquyam erat, sed diam volest.",
            "Lorem ipsum dolor sit amet, consetetur sadipscing elitr, "
            "sed diam nonumy eirmod tempor invidunt ut labore ",
            10,
        ),
    ]

    for org, short, number in tests:
        assert delete_last_word(org, number) == short


@pytest.mark.parametrize("cls", [FocusLineBoxColor, FocusLineBoxTop, FocusLineBoxWidth])
def test_focus_line_box(cls):
    inner = urwid.Filler(urwid.Text("test"))
    box = cls(inner)
    assert box.original_widget is inner
    box.render((20, 10), focus=False)
    box.render((20, 10), focus=True)
