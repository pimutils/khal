"""floating boxes (dialogs, help), the grey backdrop, header messages, event details"""

import datetime as dt

import pytest
import urwid

from khal import ui
from khal.settings import get_config
from khal.ui import colors
from khal.ui.base import Window
from khal.ui.details import EventDetails
from khal.ui.floating import Answer, ChoiceDialog, HelpView, describe_rrule, help_groups
from tests.utils import _get_text, cal1

ICS = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//test//EN
BEGIN:VEVENT
SUMMARY:Standup
DTSTART;TZID=Europe/Berlin:20261126T090000
DTEND;TZID=Europe/Berlin:20261126T091500
DTSTAMP:20261101T000000Z
UID:standup
LOCATION:Room 2.04
RRULE:FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR
ATTENDEE;PARTSTAT=ACCEPTED:mailto:alice@example.org
ATTENDEE;PARTSTAT=DECLINED:mailto:carol@example.org
ATTENDEE:mailto:bob@example.org
DESCRIPTION:Bring coffee.
BEGIN:VALARM
ACTION:DISPLAY
DESCRIPTION:Standup
TRIGGER:-PT5M
END:VALARM
END:VEVENT
END:VCALENDAR
"""


def text(widget, size):
    return "\n".join(line.decode().rstrip() for line in widget.render(size, True).text)


@pytest.fixture
def conf():
    return get_config(
        "tests/configs/small.conf",
        _get_color_from_vdir=lambda path: None,
        _get_vdir_type=lambda path: "calendar",
    )


@pytest.fixture
def window(coll_vdirs, conf):
    collection, _ = coll_vdirs
    window = Window(footer="n new", version="khal v0.14.2")
    pane = ui.ClassicView(collection, conf)
    window.open(pane)
    return window


def make_dialog():
    chosen = []
    answers = [
        Answer("t", "only this one", lambda: chosen.append("t"), "Thu 26 Nov"),
        Answer("f", "this and all following", lambda: chosen.append("f")),
        Answer("a", "all occurrences", lambda: chosen.append("a")),
    ]
    dialog = ChoiceDialog(
        "Delete",
        "Delete “Standup”?",
        answers,
        lambda: chosen.append("cancel"),
        "Repeats every weekday at 09:00.",
    )
    return dialog, chosen


def test_choice_dialog_renders():
    dialog, _ = make_dialog()
    rendered = text(dialog, (dialog.width,))
    assert "╭─ Delete " in rendered
    assert "esc cancel ─╮" in rendered
    assert "▌ t  only this one" in rendered
    assert "  f  this and all following" in rendered
    assert "Repeats every weekday at 09:00." in rendered


@pytest.mark.parametrize(
    ("keys", "expected"),
    [
        (["f"], ["f"]),
        (["a"], ["a"]),
        (["esc"], ["cancel"]),
        (["enter"], ["t"]),  # the first answer has the focus
        (["down", "down", "enter"], ["a"]),
        (["x", "t"], ["t"]),  # unknown keys are passed on
    ],
)
def test_choice_dialog_keys(keys, expected):
    dialog, chosen = make_dialog()
    size = (dialog.width,)
    for key in keys:
        dialog.keypress(size, key)
    assert chosen == expected


def test_pane_choose_closes_before_callback(window):
    pane = window._get_current_pane()
    called = []
    pane.choose("Q", "Really?", [Answer("y", "yes", lambda: called.append(len(window._track)))])
    assert len(window._track) == 2
    overlay = window._get_current_pane()
    overlay.keypress((80, 24), "y")
    assert called == [1]
    assert len(window._track) == 1


def test_floating_box_uses_backdrop(window):
    palette = colors.add_backdrop_twins(list(colors.dark))
    window.backdrop = colors.backdrop_map(palette)
    pane = window._get_current_pane()
    pane.choose("Q", "Really?", [Answer("y", "yes", lambda: None)])
    overlay = window._get_current_pane()
    assert isinstance(overlay.bottom_w, urwid.AttrMap)
    assert overlay.bottom_w.attr_map[None] == "backdrop"
    assert overlay.bottom_w.attr_map["editor field"] == "editor field grey"
    # esc closes it again
    window.on_key_press(overlay.keypress((80, 24), "esc") or "")
    assert window._get_current_pane() is pane


def test_backdrop_twins():
    palette = [
        ("plain", "", ""),
        ("red", "dark red", "", "", "#ff0000", ""),
        ("blockbg", "white,bold", "dark blue"),
        ("calendar work", "", "", "", "#3366ff", ""),
    ]
    twins = {entry[0]: entry for entry in colors.add_backdrop_twins(palette)}
    assert "red grey" in twins
    assert "calendar work grey" in twins
    assert "backdrop" in twins
    name, fg16, bg16, _, fg_high, bg_high = twins["red grey"]
    assert fg16 == "light gray"  # 16 colours: one visible grey for everything
    assert bg16 == ""
    r, g, b = fg_high[1:3], fg_high[3:5], fg_high[5:7]
    assert r == g == b  # greyscale
    # blended towards the (black) background: darker than plain luminance
    assert int(r, 16) < round(0.299 * 255)
    assert twins["blockbg grey"][1] == "light gray,bold"
    assert twins["blockbg grey"][5].startswith("#")
    # light themes blend towards white
    light = {e[0]: e for e in colors.add_backdrop_twins(palette, dark_theme=False)}
    assert int(light["red grey"][4][1:3], 16) > int(r, 16)
    # all twins are valid urwid palette entries
    urwid.display.raw.Screen().register_palette(list(twins.values()))
    mapping = colors.backdrop_map(list(twins.values()))
    assert mapping["calendar work"] == "calendar work grey"
    assert "red grey" not in mapping


def test_help_groups_and_view(conf):
    extra = [("dummy view", [("something", ["x"], "do something")])]
    groups = help_groups(conf["keybindings"], extra)
    titles = [title for title, _ in groups]
    assert titles[:3] == ["Move", "Events", "View"]
    assert "dummy view" in titles
    help_view = HelpView(groups)
    wide = text(help_view, (90, 40))
    assert "new event" in wide
    assert "do something" in wide
    # two columns side by side when wide, the groups flow down the columns
    lines = wide.splitlines()
    move = next(line for line in lines if "Move" in line)
    assert "Events" not in move
    assert move.index("Move") < 3
    assert any(line.index("View") > 30 for line in lines if "View" in line)
    assert "k ↑" in wide  # letters first
    narrow = text(HelpView(groups), (40, 60))
    assert not any(len(line.strip()) > 38 for line in narrow.splitlines())
    # scrolls
    small = HelpView(groups)
    before = text(small, (40, 5))
    small.keypress((40, 5), "page down")
    assert text(small, (40, 5)) != before


def test_describe_rrule():
    import icalendar

    start = dt.datetime(2026, 11, 26, 9, 0)
    weekdays = icalendar.vRecur.from_ical("FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR")
    assert describe_rrule(weekdays, start) == "Repeats every weekday at 09:00."
    biweekly = icalendar.vRecur.from_ical("FREQ=WEEKLY;INTERVAL=2;COUNT=5")
    assert describe_rrule(biweekly, start.date()) == "Repeats every 2 weeks, 5 times."
    monthly = icalendar.vRecur.from_ical("FREQ=MONTHLY;BYDAY=1SU")
    assert describe_rrule(monthly, start.date()) == "Repeats every month on the 1st Sun."
    two = icalendar.vRecur.from_ical("FREQ=MONTHLY;BYDAY=2TU,4TH")
    assert describe_rrule(two, start) == (
        "Repeats every 2nd Tuesday and 4th Thursday of the month at 09:00."
    )
    odd = icalendar.vRecur.from_ical("FREQ=WEEKLY;BYHOUR=9,17")
    assert describe_rrule(odd, start.date()) == "Repeats every week (BYHOUR=9,17)."


def test_event_details(coll_vdirs, conf):
    collection, _ = coll_vdirs
    event = collection.create_event_from_ics(ICS, calendar_name=cal1)
    details = EventDetails(conf, event, today=dt.date(2026, 11, 25))
    rendered = text(details, (90, 20))
    lines = rendered.splitlines()
    assert lines[1].strip() == "Standup"
    assert lines[2].strip() == "● foobar · tomorrow"
    assert "when   Th 26 Nov 09:00:00–09:15:00 · 15m" in rendered  # timeformat %H:%M:%S
    assert "where  Room 2.04" in rendered
    assert "who    ✓ alice@example.org   ✗ carol@example.org   ? bob@example.org" in rendered
    assert "alarm  5 min before" in rendered
    assert "repeat every weekday at" in rendered
    assert "notes  Bring coffee." in rendered
    assert "all day" not in rendered
    assert "enter edit  d delete" in lines[-1]


def test_header_messages(window):
    window.message("Saved “X” to home", "ok")
    header = window.header.base_widget.text
    assert "✓ Saved “X” to home" in header
    window.message("permission denied", "error")
    assert "✗ permission denied  L shows the log" in window.header.base_widget.text
    window.alert(("alert", "boom"))
    assert "✗ boom" in window.header.base_widget.text
    footer = text(window.footer, (100,))
    assert "n new" in footer
    assert footer.endswith("khal v0.14.2")
    # too narrow for both: the keys win
    narrow = text(window.footer, (60,))
    assert "khal v" not in narrow
    assert narrow.startswith(" n new")


def test_editor_save_message_and_unsaved_dialog(window, conf):
    from khal.ui.editor import EventEditor

    pane = window._get_current_pane()
    event = pane.collection.create_event_from_ics(_get_text("event_dt_simple"), calendar_name=cal1)
    editor = EventEditor(pane, event, save_callback=lambda *a: None, layout="sections")
    window.open(editor)
    size = (80, 30)
    editor.render(size, True)
    editor.keypress(size, "end")
    editor.keypress(size, "!")
    # esc with changes asks
    editor.keypress(size, "esc")
    dialog = window._get_current_pane()
    assert "Unsaved changes" in text(dialog, size)
    assert "Title was changed." in text(dialog, size)
    dialog.keypress(size, "k")  # keep editing
    assert window._get_current_pane() is editor
    editor.keypress(size, "esc")
    window._get_current_pane().keypress(size, "s")  # save
    assert window._get_current_pane() is pane
    assert event.summary == "An Event!"
    assert "✓ Saved “An Event!” to foobar" in window.header.base_widget.text


def test_delete_following(coll_vdirs, conf):
    collection, _ = coll_vdirs
    event = collection.create_event_from_ics(ICS, calendar_name=cal1)
    collection.insert(event)
    instance = event.start + dt.timedelta(days=7)
    updated = collection.delete_following(event.href, event.etag, cal1, instance)
    assert updated is not None
    until = updated.recurobject["UNTIL"][0]
    assert until < instance
    # deleting from the first instance on deletes the whole event
    assert collection.delete_following(updated.href, updated.etag, cal1, event.start) is None


def test_export_dialog(window, tmp_path, monkeypatch):
    from khal.ui.editor import ExportDialog, open_export_dialog

    pane = window._get_current_pane()
    event = pane.collection.create_event_from_ics(ICS, calendar_name=cal1)
    (tmp_path / "talks-2026").mkdir()
    monkeypatch.setenv("HOME", str(tmp_path))
    dialog = open_export_dialog(window, event)
    assert isinstance(dialog, ExportDialog)
    size = (dialog.width,)
    rendered = text(dialog, size)
    assert "╭─ Export " in rendered
    assert "Export “Standup” as .ics" in rendered
    assert "file   ~/Standup.ics" in rendered
    # invalid directory: error under the field, dialog stays open
    dialog.path.set_edit_text("~/talks/Standup.ics")
    dialog.keypress(size, "enter")
    assert "✗ ~/talks does not exist" in text(dialog, size)
    assert window._get_current_pane().top_w is dialog
    # tab completes the path
    dialog.path.set_edit_text("~/tal")
    dialog.path.keypress((40,), "tab")
    assert dialog.path.get_edit_text() == "~/talks-2026/"
    dialog.path.set_edit_text("~/talks-2026/standup.ics")
    dialog.keypress(size, "enter")
    assert (tmp_path / "talks-2026" / "standup.ics").read_text().startswith("BEGIN:VCALENDAR")
    assert window._get_current_pane() is pane
    assert "✓ Exported to ~/talks-2026/standup.ics" in window.header.base_widget.text


def test_save_error_focuses_end(window):
    from khal.ui.editor import EventEditor
    from khal.ui.editor_layout import focused_field_id

    pane = window._get_current_pane()
    event = pane.collection.create_event_from_ics(_get_text("event_dt_simple"), calendar_name=cal1)
    editor = EventEditor(pane, event, save_callback=lambda *a: None, layout="sections")
    window.open(editor)
    size = (80, 30)
    editor.render(size, True)
    see = editor.startendeditor
    day_before = see.startdt.date() - dt.timedelta(days=1)
    see.widgets.enddate.date = day_before
    see._end_date_change(day_before)
    editor.save(None)
    assert window._get_current_pane() is editor  # not saved
    assert focused_field_id(editor._w) == "end"
    rendered = text(editor, size)
    assert "✗ ends before it" in rendered
    assert "✗ can't save" in rendered
    assert "✗ Can't save: the event ends before it starts" in window.header.base_widget.text


def test_unsupported_rule(window):
    from khal.ui.editor import EventEditor

    pane = window._get_current_pane()
    ics = ICS.replace("RRULE:FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR", "RRULE:FREQ=MONTHLY;BYDAY=-1FR")
    event = pane.collection.create_event_from_ics(ics, calendar_name=cal1)
    editor = EventEditor(pane, event, save_callback=lambda *a: None, layout="sections")
    size = (80, 40)
    rendered = text(editor, size)
    assert "⚠ repeats in a way ikhal can't edit:" in rendered
    assert "every month on the last Fri at 09:00" in rendered
    assert "e  edit anyway (replaces the rule)" in rendered
    editor.recurrenceeditor.keypress((60,), "e")
    rendered = text(editor, size)
    assert "can't edit" not in rendered
    assert "│ every" in rendered


def test_date_picker_style():
    from khal.ui.editor import DateEdit

    date_edit = DateEdit(dt.date(2026, 11, 26), "%Y-%m-%d", keybindings={})
    popup_launcher = date_edit._w.original_widget.original_widget
    popup = popup_launcher.create_pop_up()
    params = popup_launcher.get_pop_up_parameters()
    rendered = text(popup, (params["overlay_width"], params["overlay_height"]))
    lines = rendered.splitlines()
    assert lines[0].startswith("╭─")
    assert "enter pick · t today · esc" in rendered
    attrs = {
        attr
        for row in popup.render((params["overlay_width"], params["overlay_height"]), True).content()
        for attr, _, _ in row
    }
    assert "editor day on" in attrs  # the chosen day is filled
    assert "float border" in attrs
