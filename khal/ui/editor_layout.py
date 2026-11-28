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

"""Layouts for ikhal's event editor.

The editor's widgets are created once (by `EventEditor`, from the field
registry `FIELDS`); how they are arranged on screen is described by a
`LayoutSpec`. `LayoutBuilder` turns a spec into urwid widgets, using a few
shared primitives (`FocusRow`, `section_rule`, `Card`, the "+ field" adders
row and the action bar). The variants (`LAYOUTS`) differ only in their spec,
to add a new one, add a `LayoutSpec` to `LAYOUTS` (and to the
`editor_layout` option in khal.spec).

With the layout `auto`, `EventEditor` picks a spec from the width it gets
rendered at (see `auto_layout()`) and rebuilds when a threshold is crossed,
keeping the focus on the same field.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any, Literal

import urwid

from .widgets import (
    ActionButton,
    AlarmStyle,
    DelegateNext,
    FlowWidget,
    FocusExpand,
    LiveText,
    NColumns,
    NListBox,
    NPile,
    SupportsNext,
    calendar_mark,
    calendar_row,
    find_child,
)

if TYPE_CHECKING:
    from khal.khalendar.event import Event

    from .editor import EventEditor, StartEndEditor


# --------------------------------------------------------------------------
# glyphs


@dataclass(frozen=True)
class Glyphs:
    """all non-ASCII characters the editor draws, so they can be swapped out"""

    marker: str = "▌"
    rule: str = "─"
    arrow: str = "→"
    dot: str = "●"
    dropdown: str = " ▾"
    delete: str = "✕"
    plus: str = "+"
    alarm: str = "◔ "
    ellipsis: str = "…"
    none: str = "—"
    bar: str = "│ "
    # top left, horizontal, top right, vertical, bottom left, bottom right
    box: tuple[str, str, str, str, str, str] = ("╭", "─", "╮", "│", "╰", "╯")
    button: tuple[str, str] = (" ", " ")
    unsaved: str = "● unsaved"
    enter: str = "enter"
    error: str = "✗"


UNICODE = Glyphs()
ASCII = Glyphs(
    marker=">",
    rule="-",
    arrow="->",
    dot="*",
    dropdown=" v",
    delete="[x]",
    alarm="",
    ellipsis="...",
    none="-",
    bar="| ",
    box=("+", "-", "+", "|", "+", "+"),
    button=("[", "]"),
    unsaved="* unsaved",
    enter="enter",
    error="x",
)


# --------------------------------------------------------------------------
# field registry


LabelStyle = Literal["long", "short", "noun"]


@dataclass(frozen=True)
class FieldDef:
    """one editable field of the event editor

    A label of `None` means "no label column at all" (the content starts
    where labels would), `""` means an empty label column (the content is
    aligned with the other fields' values).
    """

    id: str
    group: Literal["event", "when", "details", "alarms"]
    kind: Literal["text", "calendar", "start", "end", "flags", "repeat", "alarms"]
    label: str | None  # long label, used by e.g. "sections"
    short: str | None  # at most four letters, used by "compact"
    noun: str | None  # short noun, used by "headline"
    name: str = ""  # used in the "+ name" adders row
    placeholder: str = ""  # `{e}` is replaced by an ellipsis, `{n}` by a dash
    optional: bool = False  # can be collapsed into the adders row when empty
    multiline: bool = False
    load: Callable[[Event], str] | None = None  # text fields only
    store: Callable[[Event, str], None] | None = None  # text fields only

    def label_for(self, style: LabelStyle) -> str | None:
        return {"long": self.label, "short": self.short, "noun": self.noun}[style]


FIELDS: tuple[FieldDef, ...] = (
    FieldDef(
        "summary",
        "event",
        "text",
        "Title",
        None,
        None,
        placeholder="New event",
        load=lambda event: event.summary,
        store=lambda event, text: event.update_summary(text),
    ),
    FieldDef("calendar", "event", "calendar", "Calendar", None, None),
    FieldDef("start", "when", "start", "Start", None, "when"),
    FieldDef("end", "when", "end", "End", None, ""),
    FieldDef("flags", "when", "flags", "", None, ""),
    FieldDef("repeat", "when", "repeat", "", None, ""),
    FieldDef(
        "location",
        "details",
        "text",
        "Location",
        "loc",
        "where",
        name="location",
        placeholder="add location {e}",
        optional=True,
        load=lambda event: event.location,
        store=lambda event, text: event.update_location(text),
    ),
    FieldDef(
        "attendees",
        "details",
        "text",
        "Attendees",
        "who",
        "who",
        name="attendees",
        placeholder="name@example.org, {e}",
        optional=True,
        multiline=True,
        load=lambda event: event.attendees,
        store=lambda event, text: event.update_attendees(text.split(",")),
    ),
    FieldDef(
        "categories",
        "details",
        "text",
        "Categories",
        "tags",
        "tags",
        name="categories",
        placeholder="{n}",
        optional=True,
        load=lambda event: event.categories,
        store=lambda event, text: event.update_categories(text.split(",")),
    ),
    FieldDef(
        "url",
        "details",
        "text",
        "URL",
        "url",
        "link",
        name="url",
        placeholder="{n}",
        optional=True,
        load=lambda event: event.url,
        store=lambda event, text: event.update_url(text),
    ),
    FieldDef(
        "description",
        "details",
        "text",
        "Notes",
        "note",
        "notes",
        name="notes",
        placeholder="description {e}",
        optional=True,
        multiline=True,
        load=lambda event: event.description,
        store=lambda event, text: event.update_description(text),
    ),
    FieldDef("alarms", "alarms", "alarms", None, "alrm", "alarm", name="alarm", optional=True),
)
FIELD: dict[str, FieldDef] = {f.id: f for f in FIELDS}
TEXT_FIELDS: tuple[FieldDef, ...] = tuple(f for f in FIELDS if f.kind == "text")
# group id, title (None: no section rule/card title)
GROUPS: tuple[tuple[str, str], ...] = (
    ("event", "Event"),
    ("when", "When"),
    ("details", "Details"),
    ("alarms", "Alarms"),
)


# --------------------------------------------------------------------------
# layout specs


@dataclass(frozen=True)
class LayoutSpec:
    name: str
    label_style: LabelStyle = "long"
    label_width: int = 12
    margin: int = 1  # blank columns left of the focus marker and at the right
    gap: int = 1  # blank columns between focus marker and label
    decoration: Literal["rule", "card", "none"] = "rule"
    top_spacing: int = 0  # blank rows at the top
    group_spacing: int = 1  # blank rows between groups
    rule_spacing: int = 0  # blank rows after a section rule
    # empty optional fields: show a placeholder or collapse into "+ field"
    empty: Literal["placeholder", "collapse"] = "placeholder"
    always_show: frozenset[str] = frozenset()  # never collapse these
    title_style: Literal["field", "headline", "bare"] = "field"
    summary_line: bool = False  # plain language summary below the title
    calendar_inline: bool = False  # calendar on the title row
    when_style: Literal["rows", "row"] = "rows"  # Start/End rows or one "when" row
    weekdays: bool = True  # show the weekday next to start and end date
    actions_rule: bool = True  # horizontal rule above the action bar
    actions_align: Literal["left", "right"] = "left"
    key_hints: bool = True
    alarm_description: bool = True
    glyphs: Glyphs = UNICODE

    @property
    def compact_units(self) -> bool:
        return self.label_style == "short"


SECTIONS = LayoutSpec("sections")
SECTIONS_AIRY = replace(
    SECTIONS,
    name="sections-airy",
    label_width=14,
    margin=3,
    top_spacing=1,
    group_spacing=2,
    rule_spacing=1,
)
HEADLINE = LayoutSpec(
    "headline",
    label_style="noun",
    label_width=8,
    decoration="none",
    top_spacing=1,
    empty="collapse",
    title_style="headline",
    summary_line=True,
    calendar_inline=True,
    when_style="row",
    weekdays=False,
)
CARDS = LayoutSpec(
    "cards",
    label_width=11,
    gap=0,
    decoration="card",
    group_spacing=0,
    empty="collapse",
    always_show=frozenset({"location", "attendees", "description", "alarms"}),
    title_style="bare",
    actions_rule=False,
)
COMPACT = LayoutSpec(
    "compact",
    label_style="short",
    label_width=5,
    gap=0,
    decoration="none",
    group_spacing=0,
    empty="collapse",
    title_style="bare",
    calendar_inline=True,
    when_style="row",
    weekdays=False,
    actions_rule=False,
    alarm_description=False,
)
COMPACT_ASCII = replace(COMPACT, name="compact-ascii", glyphs=ASCII)

LAYOUTS: dict[str, LayoutSpec] = {
    spec.name: spec for spec in (SECTIONS, SECTIONS_AIRY, HEADLINE, CARDS, COMPACT, COMPACT_ASCII)
}

# editor widths (in columns, without the frame) at which `auto` switches
AUTO_COMPACT_BELOW = 60
AUTO_AIRY_FROM = 96


def auto_layout(cols: int) -> LayoutSpec:
    """the spec `auto` uses for an editor that is `cols` columns wide"""
    if cols < AUTO_COMPACT_BELOW:
        return COMPACT
    if cols < AUTO_AIRY_FROM:
        return SECTIONS
    return SECTIONS_AIRY


# --------------------------------------------------------------------------
# formatting helpers


def format_duration(delta: dt.timedelta, compact: bool = False) -> str:
    seconds = int(delta.total_seconds())
    if seconds < 0:
        return ""
    days, seconds = divmod(seconds, 24 * 60 * 60)
    hours, seconds = divmod(seconds, 60 * 60)
    minutes = seconds // 60
    units = [(days, "d"), (hours, "h"), (minutes, "m" if compact else "min")]
    parts = [f"{value}{'' if compact else ' '}{unit}" for value, unit in units if value]
    if not parts:
        return "0m" if compact else "0 min"
    return ("" if compact else " ").join(parts)


def span_duration(start, end, allday: bool, compact: bool = True) -> str:
    """duration of an event in the one compact format used everywhere
    (`15m`, `9h30m`, `2d18h`, `2d`), allday events end on (including) `end`

    :param compact: (ignored, durations are always compact)
    """
    if allday:
        return f"{(end - start).days + 1}d"
    return format_duration(end - start, compact=True)


def event_duration(see: StartEndEditor, compact: bool = False) -> str:
    return span_duration(see.startdt, see.enddt, see.allday, compact)


def relative_day(day: dt.date, today: dt.date | None = None) -> str:
    """`today`, `tomorrow`, `in 3 days`, `2 weeks ago`, ..."""
    today = today or dt.date.today()
    delta = (day - today).days
    if delta == 0:
        return "today"
    if delta == 1:
        return "tomorrow"
    if delta == -1:
        return "yesterday"
    amount, unit = abs(delta), "day"
    if amount >= 14:
        amount, unit = amount // 7, "week"
    text = f"{amount} {unit}s"
    return f"in {text}" if delta > 0 else f"{text} ago"


def _in(delta: dt.timedelta) -> str:
    """`25m`, `2h`, `2h30m` (for "in 2h", "ended 25m ago")"""
    minutes = max(1, int(delta.total_seconds() // 60))
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h{minutes:02d}m" if minutes else f"{hours}h"
    return f"{minutes}m"


def relative_to_now(start, end, allday: bool, now: dt.datetime | None = None):
    """where an event is from now: (None, "tomorrow"), (None, "in 2h"),
    ("now", "ends in 6 days"), (None, "ended yesterday"), ...

    All-day events end at midnight after their (inclusive) last day.
    """
    now = now or dt.datetime.now()
    today = now.date()
    if allday:
        start = dt.datetime.combine(start, dt.time())
        end = dt.datetime.combine(end + dt.timedelta(days=1), dt.time())
    else:
        start = start.replace(tzinfo=None)
        end = end.replace(tzinfo=None)
    # the last day an event takes (an end at midnight belongs to the day before)
    last_day = (end - dt.timedelta(microseconds=1)).date() if end > start else start.date()
    if now < start:
        if start.date() == today:
            return None, f"in {_in(start - now)}"
        return None, relative_day(start.date(), today)
    if now < end:
        if not allday and end.date() == today:
            return "now", f"ends in {_in(end - now)}"
        if last_day == today:
            return "now", "ends today"
        return "now", f"ends {relative_day(last_day, today)}"
    if not allday and end.date() == today:
        return None, f"ended {_in(now - end)} ago"
    if last_day == today:
        return None, "ended today"
    return None, f"ended {relative_day(last_day, today)}"


def summary_line(
    calendar: str,
    start,
    end,
    allday: bool,
    conf,
    glyphs: Glyphs,
    extra: list[str] | tuple[str, ...] = (),
    attr: str = "editor dim",
    compact: bool = False,
) -> list:
    """`● work · Fri Nov 27 · 08:00–17:30 · 9 h 30 min · …` (editor), with
    `compact` `● work · Fri 27 Nov · 08:00–17:30 · 9h30m · …` (details, like
    the day headers of the list)"""
    timefmt = conf["locale"]["timeformat"]
    day = f"{start:%a} {start.day} {start:%b}" if compact else f"{start:%a %b} {start.day}"
    parts: list[str] = [day]
    if allday:
        parts.append("all day")
    elif end.date() != start.date():
        # ends on another day: name that day ("18:00 – Mon 30 Nov 12:00")
        end_day = f"{end:%a} {end.day} {end:%b}" if compact else f"{end:%a %b} {end.day}"
        parts.append(f"{start.strftime(timefmt)} – {end_day} {end.strftime(timefmt)}")
    else:
        parts.append(f"{start.strftime(timefmt)}–{end.strftime(timefmt)}")
    parts.append(span_duration(start, end, allday, compact))
    parts.extend(extra)
    return [(f"calendar {calendar} mark", glyphs.dot + " "), (attr, " · ".join([calendar, *parts]))]


def format_alarm(delta: dt.timedelta, compact: bool = False) -> str:
    direction = "after" if delta.total_seconds() > 0 else "before"
    return f"{format_duration(abs(delta), compact)} {direction}"


def when_text(see: StartEndEditor, conf, glyphs: Glyphs) -> str:
    """start and end in one line, leaving out the end date if it is redundant"""
    datefmt = conf["locale"]["longdateformat"]
    timefmt = conf["locale"]["timeformat"]
    start, end = see.startdt, see.enddt
    if see.allday:
        if start == end:
            return start.strftime(datefmt)
        return f"{start.strftime(datefmt)} {glyphs.arrow} {end.strftime(datefmt)}"
    text = f"{start.strftime(datefmt)} {start.strftime(timefmt)} {glyphs.arrow} "
    days = (end.date() - start.date()).days
    if days == 0:
        return text + end.strftime(timefmt)
    if days == 1:
        return text + f"{end.strftime(timefmt)} +1d"
    return text + f"{end.strftime(datefmt)} {end.strftime(timefmt)}"


def summary_markup(editor: EventEditor, glyphs: Glyphs) -> list:
    """plain-language summary of the edited event (for the headline layout)"""
    see = editor.startendeditor
    extra: list[str] = []
    if editor.recurrenceeditor.repeat:
        extra.append(f"repeats {editor.recurrenceeditor.recurrence_choice.active}")
    alarms = editor.alarmseditor.get_alarms()
    if len(alarms) == 1:
        extra.append(f"alarm {format_alarm(alarms[0][0])}")
    elif alarms:
        extra.append(f"{len(alarms)} alarms")
    calendar = editor.calendar_chooser.active["name"]
    return summary_line(calendar, see.startdt, see.enddt, see.allday, editor._conf, glyphs, extra)


def format_key(key: str, glyphs: Glyphs) -> str:
    """turn an urwid key name into a short hint, e.g. `ctrl s` -> `^S`"""
    if key.startswith("ctrl "):
        return "^" + key[5:].upper()
    if key.startswith("meta "):
        rest = key[5:]
        return "M-" + (glyphs.enter if rest == "enter" else rest)
    if key == "enter":
        return glyphs.enter
    if glyphs is UNICODE:
        return {
            "up": "↑",
            "down": "↓",
            "left": "←",
            "right": "→",
            " ": "space",
            "shift tab": "S-tab",
        }.get(key, key)
    return {" ": "space"}.get(key, key)


# --------------------------------------------------------------------------
# focus helpers


# the widget trees are walked with isinstance checks, so any object will do


def _wrapped(widget: object) -> object | None:
    if isinstance(widget, urwid.WidgetDecoration):
        return widget.original_widget
    if isinstance(widget, urwid.WidgetWrap):
        return widget._w
    return None


def _focus_child(widget: object) -> object | None:
    if isinstance(widget, (urwid.ListBox, urwid.Pile, urwid.Columns)):
        return widget.focus
    return _wrapped(widget)


def focused_field_id(widget: object | None) -> str | None:
    """id of the (innermost) FocusRow on the focus path below `widget`"""
    found = None
    while widget is not None:
        if isinstance(widget, FocusRow) and widget.field_id is not None:
            found = widget.field_id
        widget = _focus_child(widget)
    return found


def focus_field(widget: object, field_id: str) -> bool:
    """move the focus to the (first selectable) FocusRow of `field_id`"""
    if isinstance(widget, FocusRow) and widget.field_id == field_id:
        if widget.selectable():
            return True
    if isinstance(widget, urwid.ListBox) and isinstance(widget.body, urwid.SimpleFocusListWalker):
        for position, child in enumerate(widget.body):
            if focus_field(child, field_id):
                # via the walker: ListBox.set_focus would, on the next
                # keypress, move the focus inside `child` to the cursor column
                widget.body.set_focus(position)
                return True
        return False
    if isinstance(widget, (urwid.Pile, urwid.Columns)):
        for position, (child, _) in enumerate(widget.contents):
            if focus_field(child, field_id):
                widget.focus_position = position
                return True
        return False
    child = _wrapped(widget)
    return child is not None and focus_field(child, field_id)


# --------------------------------------------------------------------------
# primitives

# inside the focused row, these attributes get replaced so that the whole
# row shares one background
ROW_FOCUS_MAP: dict[str | None, str] = {
    None: "editor focus row",
    "editor label": "editor label focus",
    "editor placeholder": "editor placeholder focus",
    "editor field": "editor field focus",
    "editor title": "editor title focus",
    "editor dim": "editor dim focus",
    "editor rule": "editor dim focus",
    "editor delete": "editor dim focus",
    "editor adder": "editor dim focus",
    "calendar": "editor focus row",
}


class FocusRow(DelegateNext, urwid.WidgetWrap):
    """one row of the editor: [margin][marker][gap][label][content][margin]

    While (something in) the row has the focus, the marker shows the focus
    glyph and the whole row gets the focus attributes.
    """

    def __init__(
        self,
        field_id: str | None,
        content: urwid.Widget,
        *,
        label: str | tuple[str, str] | None = None,
        label_width: int = 0,
        margin: int = 1,
        gap: int = 1,
        glyphs: Glyphs = UNICODE,
        collapse_with: FlowWidget | None = None,
    ) -> None:
        """
        :param collapse_with: hide the whole row while this (flow) widget has
            no rows, e.g. the recurrence editor while not repeating
        """
        self.field_id = field_id
        self._content = content
        self._collapse_with = collapse_with
        self._glyphs = glyphs
        self._marker = urwid.Text(" ", wrap="clip")
        columns: list[Any] = []
        if margin:
            columns.append((margin, urwid.Text("")))
        columns.append((len(glyphs.marker), self._marker))
        if gap:
            columns.append((gap, urwid.Text("")))
        if label is not None:
            columns.append((label_width, urwid.Text(("editor label", label), wrap="clip")))
        columns.append(content)
        # at least one blank column at the right, so nothing touches a border
        columns.append((max(margin, 1), urwid.Text("")))
        self._columns = NColumns(columns, focus_column=len(columns) - 2)
        super().__init__(urwid.AttrMap(self._columns, {}, ROW_FOCUS_MAP))

    def _delegate_next_target(self):
        return self._content

    def selectable(self) -> bool:
        return self._content.selectable()

    def _empty(self, size) -> bool:
        if self._collapse_with is None or len(size) != 1:
            return False
        return self._collapse_with.rows((size[0],)) == 0

    def rows(self, size, focus=False):
        if self._empty(size):
            return 0
        return super().rows(size, focus)

    def render(self, size, focus=False):
        if self._empty(size):
            return urwid.SolidCanvas(" ", size[0], 0)
        marker = ("editor marker", self._glyphs.marker) if focus else " " * len(self._glyphs.marker)
        if self._marker.get_text()[0] != (marker if isinstance(marker, str) else marker[1]):
            self._marker.set_text(marker)
        return super().render(size, focus)


class Card(DelegateNext, urwid.WidgetWrap):
    """a box around a group of rows, its border lights up while it has focus

    Also the frame of floating boxes (dialogs, help), which use a fixed
    accent border and a hint (e.g. "esc cancel") at the right of the top border.
    """

    def __init__(
        self,
        title: str,
        body: urwid.Widget,
        glyphs: Glyphs = UNICODE,
        *,
        hint: str = "",
        attr: str = "editor card",
        focus_attr: str = "editor card focus",
        title_attr: str | None = None,
        hint_attr: str = "editor dim",
    ) -> None:
        tl, h, tr, v, bl, br = glyphs.box
        self._borders: list[urwid.AttrMap] = []
        self._attr, self._focus_attr = attr, focus_attr

        def border(widget):
            mapped = urwid.AttrMap(widget, attr)
            self._borders.append(mapped)
            return mapped

        title_text = urwid.Text(
            f" {title} " if title_attr is None else [" ", (title_attr, title), " "]
        )
        top_columns: list[Any] = [(2, border(urwid.Text(tl + h)))]
        if title:
            top_columns.append(("pack", border(title_text) if title_attr is None else title_text))
        top_columns.append(border(urwid.Divider(h)))
        if hint:
            top_columns.append(("pack", urwid.Text([" ", (hint_attr, hint), " "])))
            top_columns.append((2, border(urwid.Text(h + tr))))
        else:
            top_columns.append((1, border(urwid.Text(tr))))
        top = urwid.Columns(top_columns)
        middle = urwid.Columns(
            [(1, border(urwid.SolidFill(v))), body, (1, border(urwid.SolidFill(v)))],
            box_columns=[0, 2],
            focus_column=1,
        )
        bottom = urwid.Columns(
            [(1, border(urwid.Text(bl))), border(urwid.Divider(h)), (1, border(urwid.Text(br)))]
        )
        self._body = body
        super().__init__(urwid.Pile([("pack", top), middle, ("pack", bottom)], focus_item=1))

    def _delegate_next_target(self):
        return self._body

    def selectable(self) -> bool:
        return self._body.selectable()

    def render(self, size, focus=False):
        attr = self._focus_attr if focus else self._attr
        for mapped in self._borders:
            mapped.set_attr_map({None: attr})
        return super().render(size, focus)


class WrappingButtons(DelegateNext, urwid.WidgetWrap):
    """buttons placed left to right, wrapping into more rows if needed"""

    def __init__(self, buttons: list[ActionButton], spacing: int = 1) -> None:
        self._buttons = buttons
        self._spacing = spacing
        self._maxcol: int | None = None
        super().__init__(self._pile([buttons]))

    def _pile(self, lines: list[list[ActionButton]]) -> NPile:
        return NPile(
            [
                NColumns([*((b.width, b) for b in line), urwid.Text("")], dividechars=self._spacing)
                for line in lines
            ]
        )

    def _layout(self, maxcol: int) -> None:
        if maxcol == self._maxcol:
            return
        self._maxcol = maxcol
        focused = self._w.focus.focus if self._w.contents else None
        lines: list[list[ActionButton]] = [[]]
        used = 0
        for button in self._buttons:
            need = button.width + (self._spacing if lines[-1] else 0)
            if lines[-1] and used + need > maxcol:
                lines.append([])
                used, need = 0, button.width
            lines[-1].append(button)
            used += need
        pile = self._pile(lines)
        for row, line in enumerate(lines):
            if focused in line:
                pile.focus_position = row
                find_child(pile.contents[row][0], urwid.Columns).focus_position = line.index(
                    focused
                )
        self._w = pile

    def rows(self, size, focus=False):
        self._layout(size[0])
        return super().rows(size, focus)

    def render(self, size, focus=False):
        self._layout(size[0])
        return super().render(size, focus)

    def keypress(self, size, key):
        self._layout(size[0])
        return super().keypress(size, key)


class WrappingColumns(DelegateNext, urwid.WidgetWrap):
    """groups of columns in one row, or one row per group if too narrow"""

    def __init__(self, groups: list[list], dividechars: int = 1) -> None:
        self._groups = groups
        self._dividechars = dividechars
        self._wrapped: bool | None = None
        super().__init__(self._build(False))

    def _width(self) -> int:
        widths = [option[0] for group in self._groups for option in group]
        return sum(widths) + self._dividechars * (len(widths) - 1)

    def _build(self, wrapped: bool) -> urwid.Widget:
        if wrapped:
            return NPile(
                [NColumns([*group, urwid.Text("")], self._dividechars) for group in self._groups]
            )
        return NColumns(
            [*(option for group in self._groups for option in group), urwid.Text("")],
            self._dividechars,
        )

    def _adapt(self, maxcol: int) -> None:
        wrapped = self._width() > maxcol
        if wrapped != self._wrapped:
            self._wrapped = wrapped
            self._w = self._build(wrapped)

    def rows(self, size, focus=False):
        self._adapt(size[0])
        return super().rows(size, focus)

    def render(self, size, focus=False):
        self._adapt(size[0])
        return super().render(size, focus)

    def keypress(self, size, key):
        self._adapt(size[0])
        return super().keypress(size, key)


def section_rule(title: str | None, glyphs: Glyphs) -> urwid.Widget:
    """`── Title ─────────` (or just a line, if there is no title)"""
    line = urwid.AttrMap(urwid.Divider(glyphs.rule), "editor rule")
    if not title:
        return line
    head = urwid.Text([("editor rule", glyphs.rule * 2 + " "), ("editor section", title), " "])
    return urwid.Columns([("pack", head), line])


class EditorListBox(NListBox):
    """the editor's scrolling body

    Tab and shift tab move between the selectable rows; at either end the key
    is passed on (to the action bar, which is outside the list box).
    """

    def keypress(self, size, key):
        key = urwid.ListBox.keypress(self, size, key)
        if key not in ("tab", "shift tab"):
            return key
        step = 1 if key == "tab" else -1
        position = self.focus_position + step
        while 0 <= position < len(self.body):
            widget = self.body[position]
            if widget.selectable():
                self.set_focus(position, coming_from="above" if step > 0 else "below")
                # scroll now, finishing this later would move the focus
                # inside of `widget` to wherever the cursor happens to be
                self._set_focus_complete(size, focus=True)
                if isinstance(widget, SupportsNext):
                    if step > 0:
                        widget._select_first_selectable()
                    else:
                        widget._select_last_selectable()
                return None
            position += step
        return key


def dropdown_factory(glyphs: Glyphs) -> Callable[[Any], urwid.Widget]:
    """button for `Choice`: `● home ▾` instead of `< home >`"""

    def factory(label):
        if isinstance(label, list):  # calendar markup uses the popup attributes
            label = [
                (calendar_mark(attr), text) if isinstance(attr, str) else (attr, text)
                for attr, text in (
                    part if isinstance(part, tuple) else (None, part) for part in label
                )
            ]
        else:
            label = [label]
        # calendar dots keep their colour on the focused row's background
        focus_attr: dict[str | None, str] = {None: "editor field focus"}
        for part in label:
            if isinstance(part, tuple) and str(part[0]).startswith("calendar "):
                focus_attr[part[0]] = calendar_row(part[0])
        return ActionButton(
            [*label, ("editor dim", glyphs.dropdown)],
            attr="editor field",
            focus_attr=focus_attr,
        )

    return factory


# --------------------------------------------------------------------------
# the builder


@dataclass
class BuiltLayout:
    spec: LayoutSpec
    root: urwid.Widget
    listbox: EditorListBox
    footer: list[urwid.Widget]

    def content_rows(self, cols: int) -> int:
        """rows needed to show everything without scrolling"""
        walker = self.listbox.body
        assert isinstance(walker, urwid.SimpleFocusListWalker)
        return sum(w.rows((cols,)) for w in walker) + sum(w.pack((cols,))[1] for w in self.footer)


class LayoutBuilder:
    """composes the editor's (already existing) widgets according to a spec"""

    def __init__(self, editor: EventEditor, spec: LayoutSpec) -> None:
        self.editor = editor
        self.spec = spec
        self.glyphs = spec.glyphs
        # rows inside a card don't need the outer margin, the card has it
        self._margin = 0 if spec.decoration == "card" else spec.margin

    # -- primitives bound to the spec

    def label(self, field_id: str) -> str | None:
        return FIELD[field_id].label_for(self.spec.label_style)

    def row(
        self,
        field_id: str | None,
        content: urwid.Widget,
        label: Any = ...,
        collapse_with: FlowWidget | None = None,
    ) -> FocusRow:
        if label is ...:
            label = self.label(field_id) if field_id else None
        return FocusRow(
            field_id,
            content,
            label=label,
            label_width=self.spec.label_width,
            margin=self._margin,
            gap=self.spec.gap,
            glyphs=self.glyphs,
            collapse_with=collapse_with,
        )

    def indent(self, widget: urwid.Widget) -> urwid.Padding:
        """align a non-field widget with the labels"""
        left = self._margin + len(self.glyphs.marker) + self.spec.gap
        # the right edge of FocusRow's content
        return urwid.Padding(widget, left=left, right=max(self._margin, 1))

    def blank(self, rows: int) -> list[urwid.Widget]:
        return [urwid.Divider() for _ in range(rows)]

    def text(self, template: str) -> str:
        return template.format(e=self.glyphs.ellipsis, n=self.glyphs.none)

    def button(self, label: str, on_press, attr="editor button") -> ActionButton:
        left, right = self.glyphs.button
        if attr != "editor button":  # adders, delete: no button decoration
            left, right = "", ""
        return ActionButton(
            f"{left}{label}{right}", on_press, attr=attr, focus_attr=attr + " focus"
        )

    # -- what is shown

    def collapsed(self, field_id: str) -> bool:
        field = FIELD[field_id]
        if not field.optional or self.spec.empty != "collapse":
            return False
        if field_id in self.spec.always_show or field_id in self.editor.expanded:
            return False
        if field.kind == "alarms":
            return not self.editor.alarmseditor.alarm_editors
        return self.editor.fields[field_id].original_widget.edit_text == ""

    # -- groups

    def restyle_calendar(self) -> None:
        dot = self.glyphs.dot
        chooser = self.editor.calendar_chooser.original_widget
        chooser._decorate = lambda c: [(f"calendar {c['name']} popup", dot + " "), c["name"]]
        chooser.set_button_factory(dropdown_factory(self.glyphs))

    def calendar_width(self) -> int:
        chooser = self.editor.calendar_chooser.original_widget
        longest = max(len(c["name"]) for c in chooser.choices)
        return len(self.glyphs.dot) + 1 + longest + len(self.glyphs.dropdown)

    def title_rows(self) -> list[urwid.Widget]:
        editor, spec = self.editor, self.spec
        title = editor.fields["summary"]
        if spec.title_style == "headline":
            title.set_attr_map({None: "editor headline"})
            title.set_focus_map({None: "editor headline focus"})
        else:
            title.set_attr_map({None: "editor title"})
            title.set_focus_map({None: "editor title focus"})
        label = self.label("summary") if spec.title_style == "field" else None
        if spec.calendar_inline:
            width = self.calendar_width()
            content = NColumns(
                [title, (width, editor.calendar_chooser)], dividechars=1, focus_column=0
            )
            rows: list[urwid.Widget] = [self.row("summary", content, label)]
        else:
            rows = [
                self.row("summary", title, label),
                self.row("calendar", editor.calendar_chooser, None if label is None else ...),
            ]
        if spec.summary_line:
            summary = LiveText(lambda: summary_markup(editor, self.glyphs), wrap="ellipsis")
            rows.append(self.indent(summary))
        if spec.title_style == "headline":
            rows.append(self.indent(section_rule(None, self.glyphs)))
        return rows

    def when_rows(self) -> list[urwid.Widget]:
        self.editor.startendeditor.checkallday.set_label("all day")
        self.editor.recurrenceeditor.set_external_repeat_box(True, "repeat")
        self.editor.recurrenceeditor.set_sentence_style(dropdown_factory(self.glyphs))
        if self.spec.when_style == "rows":
            arrange = self.arrange_rows
        else:
            arrange = self.arrange_row
        self.editor.startendeditor.set_arrange(arrange)
        return [self.editor.startendeditor]

    def _flags_and_repeat(self, see: StartEndEditor) -> list[urwid.Widget]:
        recurrence = self.editor.recurrenceeditor
        columns: list[Any] = [
            (len(see.checkallday.label) + 4, see.checkallday),
            (len(recurrence.repeat_box.label) + 4, recurrence.repeat_slot),
        ]
        if self.spec.when_style == "row":  # no room for problems on the when row
            columns.append(LiveText(lambda: see.status(self.glyphs.error), align="right"))
        flags = NColumns(columns, dividechars=2)
        bar = urwid.AttrMap(urwid.SolidFill(self.glyphs.bar.strip()), "editor rule")
        repeat = NColumns(
            [(len(self.glyphs.bar.strip()), bar), recurrence],
            dividechars=len(self.glyphs.bar) - len(self.glyphs.bar.strip()),
            box_columns=[0],
            focus_column=1,
        )
        return [self.row("flags", flags), self.row("repeat", repeat, collapse_with=recurrence)]

    def _weekday(self, getter) -> tuple[int, urwid.Widget]:
        monday = dt.date(2024, 1, 1)
        width = max(len((monday + dt.timedelta(days=i)).strftime("%a")) for i in range(7))
        return (width, LiveText(lambda: ("editor dim", getter().strftime("%a"))))

    def _duration(self, see: StartEndEditor, align="left", status=False) -> LiveText:
        """the duration, or (if `status`) a problem with the input instead"""
        compact = self.spec.compact_units

        def markup():
            problem = see.status(self.glyphs.error) if status else ""
            return problem or ("editor dim", event_duration(see, compact))

        return LiveText(markup, align=align)

    def arrange_rows(self, see: StartEndEditor) -> urwid.Widget:
        """Start and End on separate rows, then the allday/repeat checkboxes"""

        # no extra weekday if the date format shows one already
        dateformat = self.editor._conf["locale"]["longdateformat"]
        weekdays = self.spec.weekdays and "%a" not in dateformat and "%A" not in dateformat

        def line(getter, date, time, extra=None):
            columns: list[Any] = []
            if weekdays:
                columns.append(self._weekday(getter))
            columns.append((see.datewidth, date))
            if see.timewidth:
                # date   time: three columns apart, like the mockups
                columns.append((1, urwid.Text("")))
                columns.append((see.timewidth, time))
            columns.extend(extra or [urwid.Text("")])
            return NColumns(columns, dividechars=1, focus_column=1 if weekdays else 0)

        widgets = see.widgets
        status = LiveText(lambda: see.status(self.glyphs.error))
        rows = [
            self.row("start", line(lambda: see.startdt, widgets.startdate, widgets.starttime)),
            self.row(
                "end",
                line(
                    lambda: see.enddt,
                    widgets.enddate,
                    widgets.endtime,
                    [*self._duration_field(see), urwid.Padding(status, left=1)],
                ),
            ),
            *self._flags_and_repeat(see),
        ]
        return NPile(rows, focus_item=0)

    def _duration_field(self, see: StartEndEditor) -> list:
        """`for [1h30m]`: editable, enter opens a drum"""
        duration = see.widgets.duration
        assert duration is not None  # set up by StartEndEditor.toggle()
        return [
            (5, urwid.Text(("editor label", "  for"))),
            (7, urwid.AttrMap(duration, "editor field", "editor field focus")),
        ]

    def arrange_row(self, see: StartEndEditor) -> urwid.Widget:
        """everything in one "when" row, compact unless it has the focus"""
        widgets = see.widgets
        arrow = self.glyphs.arrow
        first: list[Any] = [(see.datewidth, widgets.startdate)]
        if see.timewidth:
            first.append((see.timewidth, widgets.starttime))
        first.append((len(arrow), urwid.Text(arrow)))
        second: list[Any] = [(see.datewidth, widgets.enddate)]
        if see.timewidth:
            second.append((see.timewidth, widgets.endtime))
        second.extend(self._duration_field(see))
        expanded = WrappingColumns([first, second])
        collapsed: urwid.Widget = LiveText(
            lambda: when_text(see, self.editor._conf, self.glyphs), wrap="ellipsis"
        )
        if not self.spec.summary_line:
            collapsed = urwid.Columns([collapsed, (9, self._duration(see, align="right"))])
        when: urwid.Widget = FocusExpand(collapsed, expanded)
        rows = [self.row("start", when), *self._flags_and_repeat(see)]
        return NPile(rows, focus_item=0)

    def detail_rows(self) -> list[urwid.Widget]:
        rows: list[urwid.Widget] = []
        for field in FIELDS:
            if field.group != "details" or self.collapsed(field.id):
                continue
            edit = self.editor.fields[field.id]
            placeholder = self.text(field.placeholder)
            edit.original_widget.set_placeholder(("editor placeholder", placeholder))
            rows.append(self.row(field.id, edit))
        return rows

    def alarm_rows(self) -> list[urwid.Widget]:
        if self.collapsed("alarms"):
            return []
        editor, glyphs = self.editor, self.glyphs
        label = self.label("alarms")
        add_label = f"{glyphs.plus} add" + ("" if self.spec.compact_units else " alarm")

        def row(widget, index):
            first = index == 0 or (index == -1 and not editor.alarmseditor.alarm_editors)
            row_label = label if first or label is None else ""
            return self.row("alarms", widget, row_label)

        def delete(on_press, user_data):
            button = ActionButton(
                glyphs.delete,
                on_press,
                user_data,
                attr="editor delete",
                focus_attr="editor delete focus",
            )
            return (button.width, button)

        def add(on_press):
            button = self.button(add_label, on_press, attr="editor adder")
            return NColumns([(button.width, button), urwid.Text("")])

        editor.alarmseditor.restyle(
            AlarmStyle(
                header=None,
                icon=glyphs.alarm,
                direction_width=len("before") + len(glyphs.dropdown) + 1,
                show_description=self.spec.alarm_description,
                long_units=not self.spec.compact_units,
                error_hint=f"{glyphs.error} e.g. 1h30m",
                delete=delete,
                add=add,
                row=row,
                choice_button=dropdown_factory(glyphs),
            )
        )
        return [editor.alarmseditor]

    def adders(self, groups: tuple[str, ...]) -> list[urwid.Widget]:
        """the `+ location  + url …` row for collapsed fields of `groups`"""
        buttons = []
        for field in FIELDS:
            if field.group not in groups or not self.collapsed(field.id):
                continue
            if self.spec.compact_units:
                text = f"{self.glyphs.plus}{field.short}"
            else:
                text = f"{self.glyphs.plus} {field.name}"
            button = ActionButton(
                text, self._expand, field.id, attr="editor adder", focus_attr="editor adder focus"
            )
            buttons.append(button)
        if not buttons:
            return []
        columns = WrappingButtons(buttons, spacing=1 if self.spec.compact_units else 3)
        return [self.row("adders", columns, None)]

    def _expand(self, _button, field_id: str) -> None:
        self.editor.expand(field_id)

    def action_bar(self) -> list[urwid.Widget]:
        editor, glyphs, spec = self.editor, self.glyphs, self.spec
        buttons = [self.button("Save", editor.save), self.button("Export", editor.export)]
        if spec.actions_align == "right":
            buttons.reverse()
        conf = editor._conf

        def hints():
            markup: list = []
            if not editor.status_in_frame:
                status = editor.status_markup(glyphs)
                if status:
                    markup += [*status, "  "]
            if spec.key_hints:
                save = conf["keybindings"].get("save", [])
                if save:
                    markup += [
                        ("editor key", format_key(save[0], glyphs)),
                        ("editor hint", " save  "),
                    ]
                markup += [("editor key", "esc"), ("editor hint", " cancel")]
            return markup or ""

        status = LiveText(hints, align="right" if spec.actions_align == "left" else "left")
        packed = [(button.width, button) for button in buttons]
        if spec.actions_align == "left":
            columns = NColumns([*packed, status], dividechars=1, focus_column=0)
        else:
            columns = NColumns([status, *packed], dividechars=1, focus_column=1)
        rows: list[urwid.Widget] = []
        if spec.actions_rule:
            rows.append(
                urwid.Padding(section_rule(None, glyphs), left=spec.margin, right=spec.margin)
            )
        # the buttons' text (not their padding) lines up with the labels
        pad = len(glyphs.button[0])
        indented = self.indent(columns)
        indented.left = max(0, indented.left - pad)
        rows.append(indented)
        return rows

    # -- putting it together

    def build(self) -> BuiltLayout:
        spec = self.spec
        self.restyle_calendar()
        groups: dict[str, list[urwid.Widget]] = {
            "event": self.title_rows(),
            "when": self.when_rows(),
            "details": self.detail_rows(),
            "alarms": self.alarm_rows(),
        }
        if spec.decoration != "none":  # each group gets its own adders
            groups["details"] += self.adders(("details",))
            groups["alarms"] += self.adders(("alarms",))

        body: list[urwid.Widget] = self.blank(spec.top_spacing)
        if spec.decoration == "rule":
            for index, (group, title) in enumerate(GROUPS):
                if not groups[group]:
                    continue
                if index:
                    body += self.blank(spec.group_spacing)
                    rule = section_rule(title, self.glyphs)
                    body.append(urwid.Padding(rule, left=spec.margin, right=spec.margin))
                    body += self.blank(spec.rule_spacing)
                body += groups[group]
        elif spec.decoration == "card":
            for index, (group, title) in enumerate(GROUPS):
                if not groups[group]:
                    continue
                if index:
                    body += self.blank(spec.group_spacing)
                card = Card(title, NPile(groups[group]), self.glyphs)
                body.append(urwid.Padding(card, left=spec.margin, right=spec.margin))
        else:
            body += groups["event"]
            body += self.blank(spec.group_spacing)
            body += groups["when"] + groups["details"] + groups["alarms"]
            adders = self.adders(("details", "alarms"))
            if adders:
                body += self.blank(spec.group_spacing) + adders

        listbox = EditorListBox(urwid.SimpleFocusListWalker(body))
        footer = self.action_bar()
        root = NPile(
            [("weight", 1, listbox), *[("pack", widget) for widget in footer]],
            outermost=True,
        )
        focus_field(listbox, "summary")
        return BuiltLayout(spec, root, listbox, footer)
