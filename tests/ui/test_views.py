"""tests for the pluggable views of ikhal's right column (khal.views entry points)"""

import datetime as dt

import pytest
import urwid

from khal import plugins, ui
from khal.settings import get_config


class DummyView(urwid.SolidFill):
    """minimal implementation of khal.ui.EventView"""

    def __init__(self, pane):
        super().__init__("x")
        self.pane = pane
        self.date = None
        self.updated = []

    @property
    def focus_event(self):
        return None

    @property
    def current_date(self):
        return self.date

    def ensure_date(self, day):
        self.date = day

    def update_range(self, start, end, everything=False):
        self.updated.append((start, end, everything))

    def refresh_titles(self, start, end, everything):
        pass

    def update_date_line(self):
        pass

    @classmethod
    def keybindings_help(cls, conf):
        return [("something", ["x"], "do something")]


@pytest.fixture
def conf():
    return get_config(
        "tests/configs/small.conf",
        _get_color_from_vdir=lambda path: None,
        _get_vdir_type=lambda path: "calendar",
    )


@pytest.fixture
def with_dummy_view(monkeypatch):
    monkeypatch.setattr(plugins, "get_views", lambda: {"dummy": DummyView})


def test_dummy_view_implements_protocol():
    assert isinstance(DummyView(None), ui.EventView)


def test_switch_view(coll_vdirs, conf, with_dummy_view):
    collection, _ = coll_vdirs
    pane = ui.ClassicView(collection, conf)
    column = pane.eventscolumn.original_widget
    assert isinstance(column.dlistbox, ui.DListBox)

    pane.keypress((80, 20), "w")
    view = column.dlistbox
    assert isinstance(view, DummyView)
    assert view.date == dt.date.today()
    assert "x" in pane.render((80, 10)).text[5].decode()

    # date changes in the calendar get forwarded to the active view
    pane.calendar.base_widget.set_focus_date(dt.date(2017, 3, 4))
    assert view.date == dt.date(2017, 3, 4)
    column.update(dt.date(2017, 3, 4), dt.date(2017, 3, 5), everything=False)
    assert view.updated == [(dt.date(2017, 3, 4), dt.date(2017, 3, 5), False)]

    # cycle back to the list, which follows the date from the view
    pane.keypress((80, 20), "w")
    assert isinstance(column.dlistbox, ui.DListBox)
    assert column.focus_date == dt.date(2017, 3, 4)

    # views are instantiated only once
    pane.keypress((80, 20), "w")
    assert column.dlistbox is view


def test_default_view(coll_vdirs, conf, with_dummy_view):
    collection, _ = coll_vdirs
    conf["view"]["default_view"] = "dummy"
    pane = ui.ClassicView(collection, conf)
    assert isinstance(pane.eventscolumn.original_widget.dlistbox, DummyView)


def test_unknown_default_view(coll_vdirs, conf, with_dummy_view, caplog, fix_caplog):
    collection, _ = coll_vdirs
    conf["view"]["default_view"] = "nonexistent"
    pane = ui.ClassicView(collection, conf)
    assert isinstance(pane.eventscolumn.original_widget.dlistbox, ui.DListBox)
    assert "Unknown view `nonexistent`" in caplog.text


def test_broken_view_is_dropped(coll_vdirs, conf, monkeypatch, caplog, fix_caplog):
    def broken(pane):
        raise RuntimeError("boom")

    monkeypatch.setattr(plugins, "get_views", lambda: {"broken": broken})
    collection, _ = coll_vdirs
    pane = ui.ClassicView(collection, conf)
    pane.keypress((80, 20), "w")
    assert isinstance(pane.eventscolumn.original_widget.dlistbox, ui.DListBox)
    assert "Could not load view `broken`" in caplog.text
    assert list(pane._views) == ["list"]


def test_extra_keybindings(coll_vdirs, conf, with_dummy_view):
    collection, _ = coll_vdirs
    pane = ui.ClassicView(collection, conf)
    # only the active view's keybindings are shown
    assert pane.extra_keybindings() == []
    pane.switch_view("dummy")
    assert pane.extra_keybindings() == [("dummy view", [("something", ["x"], "do something")])]
    pane.switch_view("list")
    assert pane.extra_keybindings() == []


def test_extra_keybindings_broken(coll_vdirs, conf, monkeypatch, caplog, fix_caplog):
    class Broken(DummyView):
        @classmethod
        def keybindings_help(cls, conf):
            raise RuntimeError("boom")

    monkeypatch.setattr(plugins, "get_views", lambda: {"broken": Broken})
    collection, _ = coll_vdirs
    pane = ui.ClassicView(collection, conf)
    pane.switch_view("broken")
    assert pane.extra_keybindings() == []
    assert "Could not get keybindings of view `broken`" in caplog.text
