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

import datetime as dt
import functools
import logging
import time
from collections.abc import Callable
from dataclasses import replace
from typing import TYPE_CHECKING, Literal

import icalendar
import urwid

from khal.utils import get_weekday_occurrence, get_wrapped_text

from .calendarwidget import CalendarWidget
from .drum import Drum, DrumColumn, DrumPopUp
from .editor_layout import (
    ASCII,
    AUTO_COMPACT_BELOW,
    COMPACT,
    COMPACT_ASCII,
    FIELD,
    FIELDS,
    LAYOUTS,
    TEXT_FIELDS,
    BuiltLayout,
    LayoutBuilder,
    LayoutSpec,
    auto_layout,
    focus_field,
    focused_field_id,
)
from .floating import FULL_WEEKDAYS, Answer, float_box
from .widgets import (
    ActionButton,
    AlarmsEditor,
    CAttrMap,
    Choice,
    CPadding,
    DateConversionError,
    DateWidget,
    DelegateNext,
    ExtendedEdit,
    LiveText,
    LiveValidatedEdit,
    NColumns,
    NPile,
    PlaceholderEdit,
    PositiveIntEdit,
    Size,
    TimeWidget,
    format_duration_short,
    parse_duration,
)

if TYPE_CHECKING:
    import khal.khalendar.event

logger = logging.getLogger("khal")


class StartEnd:
    def __init__(self, startdate, starttime, enddate, endtime) -> None:
        """collecting some common properties"""
        self.startdate = startdate
        self.starttime = starttime
        self.enddate = enddate
        self.endtime = endtime
        # the editable duration ("for 1h30m"), set by StartEndEditor.toggle()
        self.duration: urwid.Widget | None = None


class CalendarPopUp(urwid.PopUpLauncher):
    def __init__(
        self,
        widget,
        on_date_change,
        weeknumbers: Literal["left", "right", False] = False,
        firstweekday=0,
        monthdisplay="firstday",
        keybindings=None,
    ) -> None:
        self._on_date_change = on_date_change
        self._weeknumbers = weeknumbers
        self._monthdisplay = monthdisplay
        self._firstweekday = firstweekday
        self._keybindings = {} if keybindings is None else keybindings
        super().__init__(widget)

    def keypress(self, size, key):
        if key == "enter":
            self.open_pop_up()
        else:
            return super().keypress(size, key)

    def create_pop_up(self):
        def on_change(new_date):
            self.base_widget.set_value(new_date)
            self._on_date_change(new_date)

        on_press = {
            "enter": lambda _, __: self.close_pop_up(),
            "esc": lambda _, __: self.close_pop_up(),
        }
        try:
            initial_date = self.base_widget._get_current_value()
        except DateConversionError:
            return None
        else:
            today = dt.date.today()

            def styles(date: dt.date, focus: bool) -> str | None:
                if focus:
                    return "editor day on"  # the chosen day, filled
                if date == today:
                    return "float key"
                if date.weekday() >= 5:
                    return "float dim"
                return None

            calendar = CalendarWidget(
                on_change,
                self._keybindings,
                on_press,
                firstweekday=self._firstweekday,
                weeknumbers=self._weeknumbers,
                monthdisplay=self._monthdisplay,
                initial=initial_date,
                get_styles=styles,
            )
            hint = urwid.Text(("float dim", "enter pick · t today · esc"))
            body = urwid.Pile([calendar, ("pack", hint)])
            # a field pop-up: no backdrop (only real dialogs get one)
            return float_box("", body)

    def get_pop_up_parameters(self):
        width = 32 if self._weeknumbers == "right" else 28
        return {"left": 0, "top": 1, "overlay_width": width + 4, "overlay_height": 11}


class DateEdit(urwid.WidgetWrap):
    """Widget that allows editing a Date.

    Will open a calendar when `enter` is pressed, pressing `enter` again will
    select that date.
    """

    def __init__(
        self,
        startdt: dt.date,
        dateformat: str = "%Y-%m-%d",
        on_date_change: Callable = lambda _: None,
        weeknumbers: Literal["left", "right", False] = False,
        firstweekday: int = 0,
        monthdisplay: Literal["firstday", "firstfullweek"] = "firstday",
        keybindings: dict[str, list[str]] | None = None,
    ) -> None:
        datewidth = len(startdt.strftime(dateformat))
        self.width = datewidth + 1
        self._dateformat = dateformat
        if startdt is None:
            startdt = dt.date.today()
        self._edit = LiveValidatedEdit(
            dateformat=dateformat,
            EditWidget=DateWidget,
            validate=self._validate,
            edit_text=startdt.strftime(dateformat),
            on_date_change=on_date_change,
        )
        wrapped = CalendarPopUp(
            self._edit, on_date_change, weeknumbers, firstweekday, monthdisplay, keybindings
        )
        padded = CAttrMap(
            urwid.Padding(wrapped, align="left", width=datewidth, left=0, right=1),
            "calendar",
            "calendar focus",
        )
        super().__init__(padded)

    def _validate(self, text: str):
        try:
            _date = dt.datetime.strptime(text, self._dateformat).date()
        except ValueError:
            return False
        else:
            return _date

    @property
    def date(self):
        """Get currently entered date, or False, if input is invalid.

        :returns: the currently entered date
        :rtype: datetime.date
        """
        return self._validate(self._edit.get_edit_text())

    @date.setter
    def date(self, date):
        """Update text of this Widget.

        :type date: datetime.date
        """
        self._edit.base_widget.set_edit_text(date.strftime(self._dateformat))

    @property
    def valid(self) -> bool:
        return self.date is not False


class StartEndEditor(DelegateNext, urwid.WidgetWrap):
    """Widget for editing start and end times (of an event)."""

    def __init__(
        self,
        start: dt.datetime,
        end: dt.datetime,
        conf,
        on_start_date_change=lambda x: None,
        on_end_date_change=lambda x: None,
        on_type_change: Callable[[bool], None] = lambda _: None,
        arrange: "Callable[[StartEndEditor], urwid.Widget] | None" = None,
    ) -> None:
        """
        :param arrange: see `set_arrange()`
        :param on_start_date_change: a callable that gets called everytime a new
            start date is entered, with that new date as an argument
        :param on_end_date_change: same as for on_start_date_change, just for the
            end date
        :param on_type_change: callback that gets called when the event type
            (allday or datetime) changes, gets passed True if toggled to allday
            and False if toggled to daytime
        """
        self.allday = not isinstance(start, dt.datetime)
        self.conf = conf
        self._startdt: dt.date = start
        self._original_start: dt.date = start
        self._enddt: dt.date = end
        self._original_end: dt.date = end
        self.on_start_date_change = on_start_date_change
        self.on_end_date_change = on_end_date_change
        self.on_type_change = on_type_change
        self._datewidth = len(start.strftime(self.conf["locale"]["longdateformat"]))
        self._timewidth = len(start.strftime(self.conf["locale"]["timeformat"]))
        # this will contain the widgets for [start|end] [date|time]
        self.widgets = StartEnd(None, None, None, None)
        self._last_end_text: str | None = None
        self._last_start_text: str | None = None
        self._last_duration_text: str | None = None
        self._flash_until = 0.0
        self._arrange: Callable[[StartEndEditor], urwid.Widget] = arrange or self._classic_arrange
        self.checkallday = urwid.CheckBox("Allday", state=self.allday, on_state_change=self.toggle)
        self.toggle(None, self.allday)

    def keypress(self, size, key):
        return super().keypress(size, key)

    @property
    def startdt(self):
        if self.allday and isinstance(self._startdt, dt.datetime):
            return self._startdt.date()
        else:
            return self._startdt

    @property
    def _start_time(self):
        try:
            return self._startdt.time()
        except AttributeError:
            return dt.time(0)

    @property
    def localize_start(self):
        if getattr(self.startdt, "tzinfo", None) is None:
            return self.conf["locale"]["default_timezone"].localize
        else:
            return self.startdt.tzinfo.localize

    @property
    def localize_end(self):
        if getattr(self.enddt, "tzinfo", None) is None:
            return self.conf["locale"]["default_timezone"].localize
        else:
            return self.enddt.tzinfo.localize

    @property
    def enddt(self):
        if self.allday and isinstance(self._enddt, dt.datetime):
            return self._enddt.date()
        else:
            return self._enddt

    @property
    def _end_time(self):
        try:
            return self._enddt.time()
        except AttributeError:
            return dt.time(0)

    def _validate_start_time(self, text):
        try:
            startval = dt.datetime.strptime(text, self.conf["locale"]["timeformat"])
        except ValueError:
            return False
        if text != self._last_start_text:
            self._last_start_text = text
            # moving the start keeps the duration
            self._keep_duration(
                lambda: self.localize_start(
                    dt.datetime.combine(self._startdt.date(), startval.time())
                )
            )
        return startval

    def _keep_duration(self, new_start) -> None:
        """set the start to `new_start()`, move the end along"""
        try:
            delta = self._enddt - self._startdt
        except TypeError:
            delta = None
        self._startdt = new_start()
        if delta is None or getattr(self, "_initializing", False):
            return
        self._set_end(self._startdt + delta)

    def _set_end(self, end) -> None:
        """set the end (and the end widgets' texts) programmatically"""
        if isinstance(end, dt.datetime) and end.tzinfo is not None:
            # pytz timezones fix the UTC offset after arithmetic (DST changes)
            normalize = getattr(end.tzinfo, "normalize", None)
            if normalize is not None:
                end = normalize(end)
        self._enddt = end
        if self.widgets.enddate is not None:
            self.widgets.enddate.date = end.date() if isinstance(end, dt.datetime) else end
        if isinstance(end, dt.datetime) and not self.allday and self.widgets.endtime is not None:
            text = end.strftime(self.conf["locale"]["timeformat"])
            self._last_end_text = text
            self._time_edit(self.widgets.endtime).set_edit_text(text)
        self._sync_duration()

    @staticmethod
    def _time_edit(widget):
        """the urwid.Edit of a (padded, pop-up wrapped) time widget"""
        return widget.base_widget

    def _start_date_change(self, date):
        self._keep_duration(
            lambda: (
                self.localize_start(dt.datetime.combine(date, self._start_time))
                if not self.allday
                else date
            )
        )
        self.on_start_date_change(date)

    # -- duration

    def duration_text(self) -> str:
        """the duration as `1h30m` (or `3d` for all-day events)"""
        try:
            if self.allday:
                return f"{(self.enddt - self.startdt).days + 1}d"
            delta = self.enddt - self.startdt
        except TypeError:
            return ""
        if delta < dt.timedelta(0):
            return ""
        return format_duration_short(delta)

    def _sync_duration(self) -> None:
        widget = getattr(self.widgets, "duration", None)
        if widget is None:
            return
        text = self.duration_text()
        if text and text != self._time_edit(widget).get_edit_text():
            self._last_duration_text = text
            self._time_edit(widget).set_edit_text(text)

    def _validate_duration(self, text: str):
        try:
            delta = parse_duration(text)
        except ValueError:
            return False
        if self.allday and (delta.days < 1 or delta.seconds):
            return False
        if text != self._last_duration_text:
            self._last_duration_text = text
            # editing the duration moves the end
            if self.allday:
                self._set_end(self.startdt + dt.timedelta(days=delta.days - 1))
            else:
                self._set_end(self._startdt + delta)
        return True

    # -- drums

    def _minute_step(self) -> int:
        try:
            step = int(self.conf["view"].get("minute_step", 5))
        except (TypeError, ValueError):
            step = 5
        return step if 0 < step <= 30 else 5

    def _time_drum(self, edit, is_end: bool, close) -> Drum:
        timeformat = self.conf["locale"]["timeformat"]
        old_text = edit.base_widget.get_edit_text()
        try:
            current = dt.datetime.strptime(old_text, timeformat).time()
        except ValueError:
            current = self._start_time if not is_end else self._end_time
        step = self._minute_step()
        minutes = list(range(0, 60, step))
        minute_index = max(i for i, minute in enumerate(minutes) if minute <= current.minute)

        def take(values):
            hour, minute = values
            text = dt.time(hour, minute).strftime(timeformat)
            edit.base_widget.set_edit_text(text)
            edit.base_widget.set_edit_pos(len(text))
            edit._validate()  # applies it (and moves the end along / over midnight)
            close()

        def cancel():
            edit.base_widget.set_edit_text(old_text)
            close()

        def note(values, wrapped):
            hour, minute = values
            start = self._startdt.replace(tzinfo=None)
            end_day = self._enddt.date() if isinstance(self._enddt, dt.datetime) else start.date()
            candidate = dt.datetime.combine(end_day, dt.time(hour, minute))
            if candidate >= start:
                return format_duration_short(candidate - start)
            next_day = candidate + dt.timedelta(days=1) - start
            if next_day <= dt.timedelta(hours=12):
                return f"{format_duration_short(next_day)} +1d"
            return "–"

        def digits(typed):
            if len(typed) < 4:
                return None
            hour, minute = int(typed[:2]), int(typed[2:4])
            if hour > 23 or minute > 59:
                return None
            return [hour, minute - minute % step]

        return Drum(
            [
                DrumColumn(list(range(24)), current.hour, lambda h: f"{h:02d}"),
                DrumColumn(minutes, minute_index, lambda m: f"{m:02d}"),
            ],
            take,
            cancel,
            note=note if is_end else None,
            digits=digits,
        )

    def _duration_drum(self, edit, close) -> Drum:
        old_text = edit.base_widget.get_edit_text()
        timeformat = self.conf["locale"]["timeformat"]
        if self.allday:
            values = list(range(1, 61))
            current = max(1, (self.enddt - self.startdt).days + 1)

            def fmt(days):
                return f"{days}d"

            def note(row, wrapped):
                end = self.startdt + dt.timedelta(days=row[0] - 1)
                return f"until {end:%a %d}"
        else:
            values = list(range(15, 48 * 60 + 1, 15))
            try:
                minutes = int((self.enddt - self.startdt).total_seconds() // 60)
            except TypeError:
                minutes = 60
            current = min(values, key=lambda value: abs(value - minutes))

            def fmt(value):
                return format_duration_short(dt.timedelta(minutes=value))

            def note(row, wrapped):
                end = self._startdt + dt.timedelta(minutes=row[0])
                days = (end.date() - self._startdt.date()).days
                return end.strftime(timeformat) + (f" +{days}d" if days else "")

        def take(row):
            text = fmt(row[0])
            edit.base_widget.set_edit_text(text)
            edit._validate()
            close()

        def cancel():
            edit.base_widget.set_edit_text(old_text)
            close()

        return Drum(
            [DrumColumn(values, values.index(current), fmt, wrap=False)], take, cancel, note=note
        )

    def _validate_end_time(self, text):
        try:
            endval = dt.datetime.strptime(text, self.conf["locale"]["timeformat"])
        except ValueError:
            return False
        if text != self._last_end_text:
            self._last_end_text = text
            self._enddt = self.localize_end(dt.datetime.combine(self._enddt.date(), endval.time()))
            self._roll_end_over()
            self._sync_duration()
        return endval

    def _roll_end_over(self) -> None:
        """end time entered earlier than the start on the same day: next day"""
        start, end = self._startdt, self._enddt
        if not isinstance(start, dt.datetime) or not isinstance(end, dt.datetime):
            return
        try:
            if end.date() == start.date() and end < start:
                rolled = self.localize_end(
                    dt.datetime.combine(end.date() + dt.timedelta(days=1), end.time())
                )
                self._enddt = rolled
                self.widgets.enddate.date = rolled.date()
                self._flash_until = time.monotonic() + self.FLASH_SECONDS
        except TypeError:  # aware vs. floating
            return

    FLASH_SECONDS = 2.0

    def _time_valid(self, widget) -> bool:
        if self.allday:
            return True
        text = self._time_edit(widget).get_edit_text()
        try:
            dt.datetime.strptime(text, self.conf["locale"]["timeformat"])
        except ValueError:
            return False
        return True

    def status(self, glyphs_error: str = "✗") -> str | tuple[str, str]:
        """a problem with the entered values (or a short note), "" if all is fine"""
        widgets = self.widgets
        if not widgets.startdate.valid or not widgets.enddate.valid:
            return ("editor error hint", f"{glyphs_error} not a valid date")
        if not self._time_valid(widgets.starttime) or not self._time_valid(widgets.endtime):
            return ("editor error hint", f"{glyphs_error} not a valid time")
        if not self.validate():
            return ("editor error hint", f"{glyphs_error} ends before it starts")
        if time.monotonic() < self._flash_until:
            return ("editor flash", "+1d, ends the next day")
        return ""

    def _end_date_change(self, date):
        if self.allday:
            self._enddt = date
        else:
            self._enddt = self.localize_end(dt.datetime.combine(date, self._end_time))
        self._sync_duration()
        self.on_end_date_change(date)

    def _timed_from_allday(self) -> tuple[dt.datetime, dt.datetime]:
        """start and end for unticking "all day"

        Restores the times the event had before it was made all-day; an
        event that was all-day from the start begins at 00:00 and lasts
        `default_event_duration` (single day) or until 00:00 plus that
        duration on its last day.
        """
        default = self.conf.get("default", {}).get("default_event_duration", dt.timedelta(hours=1))
        start_time, end_time, duration = getattr(self, "_timed_times", (dt.time(0), None, default))
        start = dt.datetime.combine(self._startdt, start_time)
        if self._enddt <= self._startdt:  # a single day
            end = start + (duration if duration > dt.timedelta(0) else default)
        elif end_time is not None:
            end = dt.datetime.combine(self._enddt, end_time)
        else:
            end = dt.datetime.combine(self._enddt, start_time) + default
        if end <= start:
            end = start + default
        return start, end

    def toggle(self, checkbox, state: bool):
        """change from allday to datetime event

        :param checkbox: the checkbox instance that is used for toggling, gets
                         automatically passed by urwid (is not used)
        :type checkbox: checkbox
        :param state: state the event will toggle to;
                      True if allday event, False if datetime
        """

        if self.allday is True and state is False:
            self._startdt, self._enddt = self._timed_from_allday()
        elif self.allday is False and state is True:
            assert isinstance(self._startdt, dt.datetime)
            assert isinstance(self._enddt, dt.datetime)
            # remember the times, so unticking "all day" again restores them
            # instead of collapsing the event to 00:00–00:00
            self._timed_times = (
                self._startdt.time(),
                self._enddt.time(),
                self._enddt - self._startdt,
            )
            self._startdt = self._startdt.date()
            self._enddt = self._enddt.date()
        self.allday = state
        self.widgets.startdate = DateEdit(
            self._startdt,
            self.conf["locale"]["longdateformat"],
            self._start_date_change,
            self.conf["locale"]["weeknumbers"],
            self.conf["locale"]["firstweekday"],
            self.conf["view"]["monthdisplay"],
            self.conf["keybindings"],
        )
        self.widgets.enddate = DateEdit(
            self._enddt,
            self.conf["locale"]["longdateformat"],
            self._end_date_change,
            self.conf["locale"]["weeknumbers"],
            self.conf["locale"]["firstweekday"],
            self.conf["view"]["monthdisplay"],
            self.conf["keybindings"],
        )

        if state is True:  # allday event
            self.on_type_change(True)
            self.widgets.starttime = urwid.Text("")
            self.widgets.endtime = urwid.Text("")
        elif state is False:  # datetime event
            self.on_type_change(False)
            raw_start_time_widget = LiveValidatedEdit(
                dateformat=self.conf["locale"]["timeformat"],
                EditWidget=TimeWidget,
                validate=self._validate_start_time,
                edit_text=self.startdt.strftime(self.conf["locale"]["timeformat"]),
            )
            self.widgets.starttime = urwid.Padding(
                DrumPopUp(
                    raw_start_time_widget,
                    functools.partial(self._time_drum, raw_start_time_widget, False),
                ),
                align="left",
                width=self._timewidth + 1,
                left=1,
            )

            raw_end_time_widget = LiveValidatedEdit(
                dateformat=self.conf["locale"]["timeformat"],
                EditWidget=TimeWidget,
                validate=self._validate_end_time,
                edit_text=self.enddt.strftime(self.conf["locale"]["timeformat"]),
            )
            self.widgets.endtime = urwid.Padding(
                DrumPopUp(
                    raw_end_time_widget,
                    functools.partial(self._time_drum, raw_end_time_widget, True),
                ),
                align="left",
                width=self._timewidth + 1,
                left=1,
            )
            self._last_start_text = raw_start_time_widget.get_edit_text()
            self._last_end_text = raw_end_time_widget.get_edit_text()
        duration_edit = LiveValidatedEdit(
            edit_text=self.duration_text(), validate=self._validate_duration
        )
        self._last_duration_text = duration_edit.get_edit_text()
        self.widgets.duration = DrumPopUp(
            duration_edit, lambda close: self._duration_drum(duration_edit, close)
        )
        self._rearrange()

    @property
    def datewidth(self) -> int:
        return self._datewidth

    @property
    def timewidth(self) -> int:
        """width of a time widget (including its one column left padding), 0 if allday"""
        return 0 if self.allday else self._timewidth + 1

    def set_arrange(self, arrange: Callable[["StartEndEditor"], urwid.Widget] | None) -> None:
        """set the function that arranges this editor's widgets

        `arrange` gets this editor and returns the widget to display; it is
        called again every time the widgets are recreated (e.g. when toggling
        allday). `None` selects the classic layout.
        """
        self._arrange = arrange or self._classic_arrange
        self._rearrange()

    def _rearrange(self) -> None:
        old = getattr(self, "_w", None)
        focus_id = focused_field_id(old) if old is not None else None
        urwid.WidgetWrap.__init__(self, self._arrange(self))
        if focus_id is not None:
            focus_field(self._w, focus_id)

    @staticmethod
    def _classic_arrange(see: "StartEndEditor") -> urwid.Widget:
        timewidth = see.timewidth or 1
        return NPile(
            [
                see.checkallday,
                NColumns(
                    [
                        (5, urwid.Text("From:")),
                        (see._datewidth, see.widgets.startdate),
                        (timewidth, see.widgets.starttime),
                    ],
                    dividechars=1,
                ),
                NColumns(
                    [
                        (5, urwid.Text("To:")),
                        (see._datewidth, see.widgets.enddate),
                        (timewidth, see.widgets.endtime),
                    ],
                    dividechars=1,
                ),
            ],
            focus_item=1,
        )

    @property
    def changed(self):
        """returns True if content has been edited, False otherwise"""
        return (self.startdt != self._original_start) or (self.enddt != self._original_end)

    def validate(self):
        return self.startdt <= self.enddt


class EventEditor(urwid.WidgetWrap):
    """Widget that allows Editing one `Event()`

    The widgets for all fields (see `editor_layout.FIELDS`) are created once
    here, how they are arranged is decided by a `LayoutSpec` (see
    `khal.ui.editor_layout`), selected by `[view] editor_layout`.
    """

    def __init__(
        self,
        pane,
        event: "khal.khalendar.event.Event",
        save_callback=None,
        always_save: bool = False,
        layout: str | None = None,
    ) -> None:
        """
        :param save_callback: call when saving event with new start and end
             dates and recursiveness of original and edited event as parameters
        :type save_callback: callable
        :param always_save: save event even if it has not changed
        :param layout: name of the layout (one of `editor_layout.LAYOUTS` or
             `auto`), defaults to `[view] editor_layout`
        """
        self.pane = pane
        self.event = event
        self._save_callback = save_callback

        self.collection = pane.collection
        self._conf = pane._conf

        # optional fields the user has expanded from the "+ field" row
        self.expanded: set[str] = set()
        # the last attempt to save failed (shown in the action bar until fixed)
        self.save_failed = False

        # TODO make sure recurrence rules cannot be edited if we only
        # edit one instance (or this and future) (once we support that)
        self.recurrenceeditor = RecurrenceEditor(
            self.event.recurobject,
            self._conf,
            event.start_local,
        )
        self.startendeditor = StartEndEditor(
            event.start_local,
            event.end_local,
            self._conf,
            self.start_datechange,
            self.end_datechange,
            self.type_change,
        )

        # one widget per text field of the registry
        self.fields: dict[str, urwid.AttrMap] = {}
        for field in TEXT_FIELDS:
            assert field.load is not None
            self.fields[field.id] = urwid.AttrMap(
                PlaceholderEdit(edit_text=field.load(event), multiline=field.multiline),
                "editor field",
                "editor field focus",
            )
        self.summary = self.fields["summary"]
        self.description = self.fields["description"]
        self.location = self.fields["location"]
        self.categories = self.fields["categories"]
        self.attendees = self.fields["attendees"]
        self.url = self.fields["url"]

        def decorate_choice(c) -> tuple[str, str]:
            return ("calendar " + c["name"] + " popup", c["name"])

        self.calendar_chooser = CAttrMap(
            Choice(
                [self.collection._calendars[c] for c in self.collection.writable_names],
                self.collection._calendars[self.event.calendar],
                decorate_choice,
            ),
            "editor field",
        )
        self.alarmseditor: AlarmsEditor = AlarmsEditor(self.event)
        self._always_save = always_save

        if layout is None:
            layout = self._conf["view"].get("editor_layout", "auto")
        if layout != "auto" and layout not in LAYOUTS:
            raise ValueError(f"unknown editor layout `{layout}`")
        self._layout_name = layout
        self._layout: BuiltLayout | None = None
        self._layout_size: Size | None = None
        urwid.WidgetWrap.__init__(self, urwid.SolidFill(" "))
        self._apply_layout(LAYOUTS["sections"] if layout == "auto" else LAYOUTS[layout])

    @property
    def layout(self) -> LayoutSpec:
        """the spec of the layout currently shown"""
        assert self._layout is not None
        return self._layout.spec

    def _apply_layout(self, spec: LayoutSpec, focus: str | None = None) -> None:
        """(re)build the widget tree for `spec`, keeping the focused field"""
        if focus is None and self._layout is not None:
            focus = focused_field_id(self._w)
        if not self._conf["locale"].get("unicode_symbols", True) and spec.glyphs is not ASCII:
            spec = replace(spec, glyphs=ASCII)
        self._layout = LayoutBuilder(self, spec).build()
        self._w = self._layout.root
        if focus is not None:
            focus_field(self._w, focus) or self._focus_group_of(focus)

    def _focus_group_of(self, field_id: str) -> bool:
        group = FIELD[field_id].group if field_id in FIELD else None
        return any(focus_field(self._w, field.id) for field in FIELDS if field.group == group)

    @property
    def compact_below(self) -> int:
        """editor width below which an explicitly chosen layout falls back to
        compact (`[view] editor_compact_below`, 0: never)"""
        value = self._conf["view"].get("editor_compact_below", AUTO_COMPACT_BELOW)
        return AUTO_COMPACT_BELOW if value is None else int(value)

    def wanted_layout(self, cols: int) -> LayoutSpec:
        """the layout for an editor `cols` columns wide"""
        if self._layout_name == "auto":
            return auto_layout(cols)
        spec = LAYOUTS[self._layout_name]
        if spec.name.startswith("compact") or not self.compact_below:
            return spec
        if cols < self.compact_below:
            return COMPACT_ASCII if spec.glyphs is ASCII else COMPACT
        return spec

    def _ensure_layout(self, size: Size) -> None:
        """pick the layout matching `size` (`auto`, or the narrow fallback
        of an explicitly chosen layout), keeping the focused field"""
        if size == self._layout_size or not size:
            return
        self._layout_size = size
        spec = self.wanted_layout(size[0])
        if spec.name != self.layout.name:
            self._apply_layout(spec)
        if spec.name == "sections-airy" and len(size) == 2:
            # not enough rows for the airy spacing: fall back to sections
            assert self._layout is not None
            if self._layout.content_rows(size[0]) > size[1]:
                self._apply_layout(LAYOUTS["sections"])

    # -- the status (unsaved, can't save), shown in the frame or the action bar

    # set by whoever draws the editor in a frame with a status (see
    # khal.ui.EventColumn.edit), the action bar then leaves it out
    status_in_frame = False

    def status_markup(self, glyphs=None) -> list:
        """`● unsaved`, `✗ can't save` or nothing"""
        glyphs = glyphs or self.layout.glyphs
        if self.save_failed and not self.startendeditor.validate():
            return [("message error", f"{glyphs.error} can't save")]
        if self.changed:
            return [("editor status", glyphs.unsaved)]
        return []

    def expand(self, field_id: str) -> None:
        """show the (collapsed) optional field `field_id` and focus it"""
        self.expanded.add(field_id)
        if field_id == "alarms" and not self.alarmseditor.get_alarms():
            self.alarmseditor.add_alarm(None)
        self._apply_layout(self.layout, focus=field_id)

    def render(self, size, focus=False):
        self._ensure_layout(size)
        LiveText.refresh_all()
        return super().render(size, focus)

    def start_datechange(self, date):
        self.pane.eventscolumn.original_widget.set_focus_date(date)
        self.recurrenceeditor.update_startdt(date)

    def end_datechange(self, date):
        self.pane.eventscolumn.original_widget.set_focus_date(date)

    def type_change(self, allday: bool) -> None:
        """when the event type changes, we might want to change the default alarms

        :params allday: True if the event is now an allday event, False if it isn't
        """
        # test if self.alarmseditor exists
        if not hasattr(self, "alarmseditor"):
            return

        # to make the alarms before the event, we need to set it them to
        # negative values
        default_event_alarm = -1 * self._conf["default"]["default_event_alarm"]
        default_dayevent_alarm = -1 * self._conf["default"]["default_dayevent_alarm"]
        alarms = self.alarmseditor.get_alarms()
        if len(alarms) == 1:
            timedelta = alarms[0][0]
            if allday and timedelta == default_event_alarm:
                self.alarmseditor.clear()
                self.alarmseditor.add_alarm(None, default_dayevent_alarm)
            elif (not allday) and timedelta == default_dayevent_alarm:
                self.alarmseditor.clear()
                self.alarmseditor.add_alarm(None, default_event_alarm)
            else:
                # either there were more than one alarm or the alarm was not the default
                pass

    @property
    def title(self):  # Window title
        return f"Edit: {get_wrapped_text(self.summary)}"

    @classmethod
    def selectable(cls):
        return True

    @property
    def changed(self):
        for field in TEXT_FIELDS:
            assert field.load is not None
            if get_wrapped_text(self.fields[field.id]) != field.load(self.event):
                return True
        if self.startendeditor.changed or self.calendar_chooser.changed:
            return True
        if self.recurrenceeditor.changed:
            return True
        if self.alarmseditor.changed:
            return True
        return False

    def update_vevent(self):
        for field in TEXT_FIELDS:
            assert field.store is not None
            field.store(self.event, get_wrapped_text(self.fields[field.id]))

        if self.startendeditor.changed:
            self.event.update_start_end(self.startendeditor.startdt, self.startendeditor.enddt)
        if self.recurrenceeditor.changed:
            rrule = self.recurrenceeditor.active
            self.event.update_rrule(rrule)

        if self.alarmseditor.changed:
            self.event.update_alarms(self.alarmseditor.get_alarms())

    def export(self, button):
        """export the event as ICS (asks for the path)"""
        open_export_dialog(self.pane.window, self.event)

    def save(self, button):
        """saves the event to the db

        (only when it has been changed or always_save is set)
        :param button: not needed, passed via the button press
        """
        if not self.startendeditor.validate():
            # point at the problem: focus the end, it shows "✗ ends before it starts"
            self.save_failed = True
            focus_field(self._w, "end") or focus_field(self._w, "start")
            self.pane.window.message("Can't save: the event ends before it starts", "error")
            return
        self.save_failed = False

        saved = False
        if self._always_save or self.changed is True:
            self.update_vevent()
            self.event.allday = self.startendeditor.allday
            self.event.increment_sequence()
            calendar = self.calendar_chooser.original_widget.active["name"]
            try:
                if self.event.etag is None:  # has not been saved before
                    self.event.calendar = calendar
                    self.collection.insert(self.event)
                elif self.calendar_chooser.changed:
                    self.collection.change_collection(self.event, calendar)
                else:
                    self.collection.update(self.event)
            except Exception as error:  # keep the editor open, nothing is lost
                logger.exception(error)
                self.pane.window.message(
                    f"Could not save to calendar “{calendar}”: {error}", "error"
                )
                return
            saved = True

            self._save_callback(
                self.event.start_local,
                self.event.end_local,
                self.event.recurring or self.recurrenceeditor.changed,
            )
        self.pane.window.backtrack()
        if saved:
            self.pane.window.message(f"Saved “{self.event.summary}” to {self.event.calendar}", "ok")

    def changed_parts(self) -> list[str]:
        """human names of the parts that were changed (for the unsaved dialog)"""
        parts = [
            (field.label or field.name).lower()
            for field in TEXT_FIELDS
            if field.load is not None
            and get_wrapped_text(self.fields[field.id]) != field.load(self.event)
        ]
        if self.calendar_chooser.changed:
            parts.append("calendar")
        if self.startendeditor.changed:
            parts.append("time")
        if self.recurrenceeditor.changed:
            parts.append("repetition")
        if self.alarmseditor.changed:
            parts.append("alarms")
        return parts

    def ask_unsaved(self) -> None:
        """esc with unsaved changes: save, discard or keep editing?"""
        parts = self.changed_parts()
        if len(parts) > 1:
            what = ", ".join(parts[:-1]) + " and " + parts[-1]
        else:
            what = parts[0] if parts else "the event"
        description = f"{what[0].upper()}{what[1:]} {'were' if len(parts) > 1 else 'was'} changed."
        title = get_wrapped_text(self.summary) or "New event"
        self.pane.choose(
            "Unsaved changes",
            f"Save changes to “{title}”?",
            [
                Answer("s", "save", lambda: self.save(None)),
                Answer("d", "discard", self.pane.window.backtrack),
                Answer("k", "keep editing", lambda: None),
            ],
            description=description,
        )

    def keypress(self, size: Size, key: str) -> str | None:
        if key in ["esc"] and self.changed:
            self.ask_unsaved()
            return None
        self._ensure_layout(size)
        return_value = super().keypress(size, key)
        if key in self.pane._conf["keybindings"]["save"]:
            self.save(None)
            return None
        return return_value


WEEKDAYS = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]  # TODO use locale and respect weekdaystart


class DayToggle(urwid.WidgetWrap):
    """a weekday (`Mo`) that is switched on and off with space/enter or a click"""

    def __init__(self, code: str, state: bool = False) -> None:
        self.label = code  # e.g. MO, as used in rrules
        self._icon = urwid.SelectableIcon(code.title(), 0)
        self._attr = urwid.AttrMap(self._icon, "editor field", "editor field focus")
        super().__init__(self._attr)
        self.state = state

    @property
    def state(self) -> bool:
        return self._state

    @state.setter
    def state(self, value: bool) -> None:
        self._state = value
        self._attr.set_attr_map({None: "editor day on" if value else "editor field"})
        self._attr.set_focus_map({None: "editor day on" if value else "editor field focus"})

    def keypress(self, size, key):
        if key in (" ", "enter"):
            self.state = not self.state
            return None
        return key

    def mouse_event(self, size, event, button, col, row, focus):
        if event == "mouse press" and button == 1:
            self.state = not self.state
            return True
        return False


class WeekDaySelector(urwid.WidgetWrap):
    """the weekdays as toggles, wrapping into a second row if narrow"""

    def __init__(self, startdt, selected_days) -> None:
        self._weekday_boxes = {day: DayToggle(day) for day in WEEKDAYS}
        weekday = startdt.weekday()
        self._weekday_boxes[WEEKDAYS[weekday]].state = True
        for day in selected_days:
            self._weekday_boxes[day].state = True
        self.weekday_checks = urwid.GridFlow(
            [self._weekday_boxes[day] for day in WEEKDAYS],
            cell_width=2,
            h_sep=1,
            v_sep=0,
            align="left",
        )
        urwid.WidgetWrap.__init__(self, self.weekday_checks)

    @property
    def days(self):
        return [day for day in WEEKDAYS if self._weekday_boxes[day].state]


class RecurrenceEditor(DelegateNext, urwid.WidgetWrap):
    def __init__(self, rrule, conf, startdt) -> None:
        self._conf = conf
        # if True, the repeat checkbox is not part of this widget but shown in
        # `repeat_slot` (which the layout places somewhere else, e.g. next to
        # the allday checkbox), and nothing is shown while not repeating
        self._external_repeat_box = False
        self.repeat_slot = urwid.WidgetPlaceholder(urwid.Text(""))
        self._startdt = startdt
        self._rrule = rrule
        self.repeat = bool(rrule)
        self._allow_edit = not self.repeat or self.check_understood_rrule(rrule)
        self.repeat_box = urwid.CheckBox(
            "Repeat: ",
            state=self.repeat,
            on_state_change=self.check_repeat,
        )

        if "UNTIL" in self._rrule:
            self._until = "Until"
        elif "COUNT" in self._rrule:
            self._until = "Repetitions"
        else:
            self._until = "Forever"

        recurrence = self._rrule["freq"][0].lower() if self._rrule else "weekly"
        self.recurrence_choice = CPadding(
            CAttrMap(
                Choice(
                    ["daily", "weekly", "monthly", "yearly"],
                    recurrence,
                    callback=self.rebuild,
                ),
                "popupper",
            ),
            align="center",
            left=2,
            right=2,
        )
        self.interval_edit = PositiveIntEdit(
            caption=("caption", "every:"),
            edit_text=str(self._rrule.get("INTERVAL", [1])[0]),
        )
        self.until_choice = CPadding(
            CAttrMap(
                Choice(
                    ["Forever", "Until", "Repetitions"],
                    self._until,
                    callback=self.rebuild,
                ),
                "popupper",
            ),
            align="center",
            left=2,
            right=2,
        )

        count = str(self._rrule.get("COUNT", [1])[0])
        self.repetitions_edit = PositiveIntEdit(edit_text=count)

        until = self._rrule.get("UNTIL", [None])[0]
        if until is None and isinstance(self._startdt, dt.datetime):
            until = self._startdt.date()
        elif until is None:
            until = self._startdt

        if isinstance(until, dt.datetime):
            until = until.date()
        self.until_edit = DateEdit(
            until,
            self._conf["locale"]["longdateformat"],
            lambda _: None,
            self._conf["locale"]["weeknumbers"],
            self._conf["locale"]["firstweekday"],
            self._conf["view"]["monthdisplay"],
        )

        # sentence style ("every 2 weeks on Mo Tu ...", set by the editor layout)
        self._sentence_button = None
        self._preview = True
        urwid.connect_signal(
            self.interval_edit.base_widget, "postchange", lambda *_: self._refresh_unit()
        )

        self._rebuild_weekday_checks()
        self._rebuild_monthly_choice()
        self._pile = pile = NPile([urwid.Text("")])
        urwid.WidgetWrap.__init__(self, pile)
        self.rebuild()

    UNITS = {"daily": "day", "weekly": "week", "monthly": "month", "yearly": "year"}
    ENDS = {"Forever": "never", "Until": "on", "Repetitions": "after"}

    @property
    def _freq_choice(self) -> Choice:
        return self.recurrence_choice.original_widget.original_widget

    @property
    def _until_choice(self) -> Choice:
        return self.until_choice.original_widget.original_widget

    def set_sentence_style(self, button_factory, preview: bool = True) -> None:
        """read like a sentence: `every [2] [weeks▾] on Mo Tu We ...`

        :param button_factory: makes the buttons of the dropdowns (see `Choice`)
        """
        self._sentence_button = button_factory
        self._preview = preview
        self.interval_edit.base_widget.set_caption("")
        self._freq_choice._decorate = self._unit_label
        self._freq_choice.set_button_factory(button_factory)
        self._until_choice._decorate = lambda end: self.ENDS.get(end, end)
        # in the list: never, after (… N times), on (… a date)
        self._until_choice.choices = ["Forever", "Repetitions", "Until"]
        self._until_choice.hints = {
            "Repetitions": "… N times",
            "Until": "… a date (date picker)",
        }
        self._until_choice.set_button_factory(button_factory)
        self._decorate_monthly()
        self.rebuild()

    def _unit_label(self, freq: str) -> str:
        unit = self.UNITS.get(freq, freq)
        return unit if self.interval_edit.base_widget.get_edit_text().strip() == "1" else unit + "s"

    def _refresh_unit(self) -> None:
        if self._sentence_button is not None and self.repeat:
            self._freq_choice.active = self._freq_choice.active
            self.rebuild()

    def _decorate_monthly(self) -> None:
        if self._sentence_button is not None:

            def decorate(text: str) -> str:
                # "on every 4th TH" -> "4th Thursday"
                words = text.removeprefix("on every ").replace(" of the month", "").split(" ")
                return " ".join(FULL_WEEKDAYS.get(word, word) for word in words)

            self.monthly_choice._decorate = decorate
            self.monthly_choice.set_button_factory(self._sentence_button)

    def next_occurrences(self, count: int = 3) -> list[dt.datetime]:
        """the next `count` instances after the event's start (for the preview)"""
        from dateutil.rrule import rrulestr

        start = self._startdt
        naive = (
            start.replace(tzinfo=None)
            if isinstance(start, dt.datetime)
            else dt.datetime.combine(start, dt.time())
        )
        rule = dict(self.rrule())
        if "until" in rule:
            until = rule["until"]
            if isinstance(until, dt.datetime):
                until = until.replace(tzinfo=None)
            else:
                until = dt.datetime.combine(until, dt.time(23, 59))
            rule["until"] = until
        text = icalendar.vRecur(rule).to_ical().decode()
        occurrences = []
        for occurrence in rrulestr(text, dtstart=naive):
            if occurrence > naive:
                occurrences.append(occurrence)
            if len(occurrences) == count:
                break
        return occurrences

    def preview_text(self) -> str:
        try:
            occurrences = self.next_occurrences()
        except Exception:  # invalid input while typing
            return ""
        if not occurrences:
            return "no further occurrences"
        text = " · ".join(f"{day:%a %m-%d}" for day in occurrences)
        return f"next: {text} …"

    def _rebuild_monthly_choice(self):
        weekday, xth = get_weekday_occurrence(self._startdt)
        ords = {1: "st", 2: "nd", 3: "rd", 21: "st", 22: "nd", 23: "rd", 31: "st"}
        self._xth_weekday = f"on every {xth}{ords.get(xth, 'th')} {WEEKDAYS[weekday]}"
        self._xth_monthday = (
            f"on every {self._startdt.day}{ords.get(self._startdt.day, 'th')} of the month"
        )
        self.monthly_choice = Choice(
            [self._xth_monthday, self._xth_weekday],
            self._xth_monthday,
            callback=self.rebuild,
        )
        if getattr(self, "_sentence_button", None) is not None:
            self._decorate_monthly()

    def _rebuild_weekday_checks(self):
        if self.recurrence_choice.active == "weekly":
            initial_days = self._rrule.get("BYDAY", [])
        else:
            initial_days = []
        self.weekday_checks = WeekDaySelector(self._startdt, initial_days)

    def update_startdt(self, startdt):
        self._startdt = startdt
        self._rebuild_weekday_checks()
        self._rebuild_monthly_choice()
        self.rebuild()

    @staticmethod
    def check_understood_rrule(rrule):
        """test if we can reproduce `rrule`."""
        keys = set(rrule.keys())
        freq = rrule.get("FREQ", [None])[0]
        unsupported_rrule_parts = {
            "BYSECOND",
            "BYMINUTE",
            "BYHOUR",
            "BYYEARDAY",
            "BYWEEKNO",
            "BYMONTH",
        }
        if keys.intersection(unsupported_rrule_parts):
            return False
        if len(rrule.get("BYMONTHDAY", [1])) > 1:
            return False
        # we don't support negative BYMONTHDAY numbers
        # don't need to check whole list, we only support one monthday anyway
        if rrule.get("BYMONTHDAY", [1])[0] < 1:
            return False
        if rrule.get("BYDAY", ["1"])[0][0] == "-":
            return False
        if rrule.get("BYSETPOS", [1])[0] != 1:
            return False
        if freq not in ["DAILY", "WEEKLY", "MONTHLY", "YEARLY"]:
            return False
        if "BYDAY" in keys and freq == "YEARLY":
            return False
        return True

    def check_repeat(self, checkbox, state):
        self.repeat = state
        self.rebuild()

    def _refill_contents(self, lines):
        while True:
            try:
                self._pile.contents.pop()
            except IndexError:
                break
        [self._pile.contents.append((line, ("pack", None))) for line in lines]

    def set_external_repeat_box(self, external: bool, label: str | None = None) -> None:
        """show the repeat checkbox in `repeat_slot` instead of inside this widget"""
        self._external_repeat_box = external
        if label is not None:
            self.repeat_box.set_label(label)
        self.rebuild()

    def rebuild(self):
        try:
            old_focus_y = self._pile.focus_position
        except IndexError:
            old_focus_y = 0
        if self._external_repeat_box and self._allow_edit:
            self.repeat_slot.original_widget = self.repeat_box
        else:
            self.repeat_slot.original_widget = urwid.Text("")
        if not self._allow_edit:
            self._rebuild_no_edit()
        elif self.repeat:
            self._rebuild_edit()
            if self._pile.contents:
                self._pile.focus_position = min(old_focus_y, len(self._pile.contents) - 1)
        else:
            self._rebuild_edit_no_repeat()

    def _rebuild_no_edit(self):
        """a rule ikhal can't represent: say what it is, offer to replace it"""
        from .floating import describe_rrule

        description = describe_rrule(self._rrule, self._startdt, self._conf["locale"]["timeformat"])
        description = description.removeprefix("Repeats ").rstrip(".")
        unicode_symbols = self._conf["locale"].get("unicode_symbols", True)
        lines = [
            urwid.Text(
                (
                    "editor status",
                    ("⚠" if unicode_symbols else "!") + " repeats in a way ikhal can't edit:",
                )
            ),
            urwid.Padding(urwid.Text(("editor field", description)), left=2),
            urwid.Columns(
                [
                    (2, urwid.Text("")),
                    (3, urwid.Text(("editor key", "e"))),
                    ActionButton(
                        "edit anyway (replaces the rule)",
                        lambda _: self._edit_anyway(),
                        attr="editor field",
                        focus_attr="editor field focus",
                    ),
                ]
            ),
        ]
        self._refill_contents(lines)
        self._pile.focus_position = 2

    def _edit_anyway(self) -> None:
        self._allow_edit = True
        self.rebuild()

    def keypress(self, size, key):
        if not self._allow_edit and key == "e":
            self._edit_anyway()
            return None
        return super().keypress(size, key)

    def _rebuild_edit_no_repeat(self):
        if self._external_repeat_box:
            self._refill_contents([])
        else:
            self._refill_contents([NColumns([(13, self.repeat_box)])])

    def _rebuild_edit(self):
        if self._sentence_button is not None:
            self._refill_contents(self._sentence_lines())
            return
        if self._external_repeat_box:
            firstline = NColumns([(13, self.interval_edit), (18, self.recurrence_choice)])
        else:
            firstline = NColumns(
                [
                    (13, self.repeat_box),
                    (18, self.recurrence_choice),
                    (13, self.interval_edit),
                ]
            )
        lines = [firstline]

        if self.recurrence_choice.active == "weekly":
            lines.append(self.weekday_checks)
        if self.recurrence_choice.active == "monthly":
            lines.append(self.monthly_choice)

        nextline = [(20, self.until_choice.original_widget)]
        if self.until_choice.active == "Until":
            nextline.append((24, self.until_edit))
        elif self.until_choice.active == "Repetitions":
            nextline.append((4, self.repetitions_edit))
        lines.append(NColumns(nextline))

        self._refill_contents(lines)

    def _sentence_lines(self) -> list[urwid.Widget]:
        def text(words: str) -> tuple[int, urwid.Text]:
            return (len(words), urwid.Text(words))

        freq = self.recurrence_choice.active
        unit_width = len(self._unit_label(freq)) + 2
        interval_width = max(1, len(self.interval_edit.base_widget.get_edit_text())) + 1
        first: list = [
            text("every"),
            (interval_width, self.interval_edit),
            (unit_width, self._freq_choice),
        ]
        if freq == "weekly":
            first += [text("on"), self.weekday_checks]
        elif freq == "monthly":
            first += [text("on the"), self.monthly_choice]
        else:
            first.append(urwid.Text(""))
        lines: list[urwid.Widget] = [NColumns(first, dividechars=1)]

        ends: list = [text("ends"), (9, self._until_choice)]
        if self.until_choice.active == "Until":
            ends.append((self.until_edit.width, self.until_edit))
        elif self.until_choice.active == "Repetitions":
            ends += [(4, self.repetitions_edit), text("times")]
        ends.append(urwid.Text(""))
        lines.append(NColumns(ends, dividechars=1))
        if self._preview:
            lines.append(LiveText(lambda: ("editor dim", self.preview_text()), wrap="ellipsis"))
        return lines

    @property
    def changed(self):
        if not self.repeat:
            return bool(self._rrule)
        try:
            original = icalendar.vRecur(self._rrule).to_ical()
            return original != icalendar.vRecur(self.rrule()).to_ical()
        except (ValueError, TypeError):  # e.g. invalid input
            return True

    def rrule(self):
        rrule = {}
        rrule["freq"] = [self.recurrence_choice.active]
        interval = int(self.interval_edit.get_edit_text())
        if interval != 1:
            rrule["interval"] = [interval]
        if rrule["freq"] == ["weekly"] and len(self.weekday_checks.days) > 1:
            rrule["byday"] = self.weekday_checks.days
        if rrule["freq"] == ["monthly"] and self.monthly_choice.active == self._xth_weekday:
            weekday, occurrence = get_weekday_occurrence(self._startdt)
            rrule["byday"] = [f"{occurrence}{WEEKDAYS[weekday]}"]
        if self.until_choice.active == "Until":
            if isinstance(self._startdt, dt.datetime):
                rrule["until"] = dt.datetime.combine(
                    self.until_edit.date,
                    self._startdt.time(),
                )
            else:
                rrule["until"] = self.until_edit.date
        elif self.until_choice.active == "Repetitions":
            rrule["count"] = int(self.repetitions_edit.get_edit_text())
        return rrule

    @property
    def active(self):
        if not self.repeat:
            return None
        else:
            return self.rrule()

    @active.setter
    def active(self, val):
        raise ValueError
        self.recurrence_choice.active = val


class PathEdit(ExtendedEdit):
    """an edit field for a file path, tab completes it"""

    def keypress(self, size, key):
        if key == "tab":
            self.complete()
            return None
        return super().keypress(size, key)

    def complete(self) -> list[str]:
        """complete the path as far as unambiguous, returns the candidates"""
        import glob
        import os

        text = self.get_edit_text()
        expanded = os.path.expanduser(text)
        matches = sorted(glob.glob(glob.escape(expanded) + "*"))
        if not matches:
            return []
        common = os.path.commonprefix(matches)
        if len(matches) == 1 and os.path.isdir(common):
            common += os.sep
        if common.startswith(os.path.expanduser("~")) and text.startswith("~"):
            common = "~" + common[len(os.path.expanduser("~")) :]
        if len(common) > len(text):
            self.set_edit_text(common)
            self.set_edit_pos(len(common))
        return matches


class ExportDialog(urwid.WidgetWrap):
    """export an event as .ics: a floating box with a path field

    Errors (e.g. a directory that does not exist) are shown under the field.
    """

    def __init__(self, event, on_export: Callable[[str], None], on_cancel: Callable[[], None]):
        self.event = event
        self._on_export = on_export
        self._on_cancel = on_cancel
        self.path = PathEdit(edit_text=f"~/{event.summary.strip()}.ics")
        self.path.set_edit_pos(len(self.path.get_edit_text()))
        self.message = urwid.Text(("float dim", "tab completes the path"))
        rows = [
            urwid.Divider(),
            urwid.Text(("float headline", f"Export “{event.summary}” as .ics")),
            urwid.Divider(),
            urwid.Columns(
                [
                    (7, urwid.Text(("float text", "file"))),
                    urwid.AttrMap(self.path, "editor field focus"),
                ]
            ),
            urwid.Padding(self.message, left=7),
            urwid.Divider(),
            urwid.Text(
                [
                    ("float key", " enter"),
                    ("float dim", " export   "),
                    ("float key", "esc"),
                    ("float dim", " cancel"),
                ]
            ),
            urwid.Divider(),
        ]
        self.pile = urwid.Pile(rows, focus_item=3)
        self.width = max(56, len(event.summary) + 24)
        super().__init__(float_box("Export", self.pile, "esc"))

    def error(self, text: str) -> None:
        self.message.set_text(("editor error hint", f"✗ {text}"))

    def export(self) -> bool:
        import os

        path = self.path.get_edit_text().strip()
        directory = os.path.dirname(os.path.expanduser(path)) or "."
        if not path:
            self.error("no file name")
            return False
        if not os.path.isdir(directory):
            shown = os.path.dirname(path) or "."
            self.error(f"{shown} does not exist")
            return False
        try:
            self._on_export(path)
        except Exception as error:
            self.error(str(error))
            return False
        return True

    def keypress(self, size, key):
        if key == "enter":
            self.export()
            return None
        if key == "esc":
            self._on_cancel()
            return None
        return super().keypress(size, key)


def open_export_dialog(window, event) -> ExportDialog:
    """ask for a path and export `event` there (editor and list of events)"""

    def export(path: str) -> None:
        event.export_ics(path)
        window.backtrack()
        window.message(f"Exported to {path}", "ok")

    dialog = ExportDialog(event, export, window.backtrack)
    window.open_floating(dialog, width=dialog.width, height="pack")
    return dialog
