[calendars]
# The *[calendars]* section is mandatory and must contain at least one subsection.
# Every subsection must have a unique name (enclosed by two square brackets).
# Each subsection needs exactly one *path* setting, everything else is optional.
# Here is a small example:
#
# .. literalinclude:: ../../tests/configs/small.conf
#  :language: ini
[[__many__]]
# The path to an existing directory where this calendar is saved as a *vdir*.
# The directory is searched for events or birthdays (see ``type``). The path
# also accepts glob expansion via `*` or `?` when type is set to discover.
# `**` means arbitrary depths of directories.
# This allows for paths such as `~/accounts/*/calendars/*`, where the
# calendars directory contains vdir directories. In addition, `~/calendars/*`
# and `~/calendars/default` are valid paths if there exists a vdir in the
# `default` directory. (The previous behavior of recursively searching
# directories has been replaced with globbing).
path = expand_path(default=None)

# khal will use this color for coloring this calendar's event.
# The following color names are supported: *black*, *white*, *brown*, *yellow*,
# *dark gray*, *dark green*, *dark blue*, *light gray*, *light green*, *light
# blue*, *dark magenta*, *dark cyan*, *dark red*, *light magenta*, *light
# cyan*, *light red*.
# Depending on your terminal emulator's settings, they might look different
# than what their name implies.
# In addition to the 16 named colors an index from the 256-color palette or a
# 24-bit color code can be used, if your terminal supports this.
# The 256-color palette index is simply a number between 0 and 255.
# The 24-bit color must be given as #RRGGBB, where RR, GG, BB is the
# hexadecimal value of the red, green and blue component, respectively.
# When using a 24-bit color, make sure to enclose the color value in ' or "!
# If `color` is set to *auto* (the default), khal looks for a color value in a
# *color* file in this calendar's vdir. If the *color* file does not exist, the
# default_color (see below) is used. If color is set to '', the default_color is
# always used. Note that you can use `vdirsyncer metasync` to synchronize colors
# with your caldav server.

color = color(default='auto')

# When coloring days, the color will be determined based on the calendar with
# the highest priority. If the priorities are equal, then the "multiple" color
# will be used.

priority = integer(default=10)

# setting this to *True*, will keep khal from making any changes to this
# calendar
readonly = boolean(default=False)

# Setting the type of this collection (default ``calendar``).
#
# If set to ``calendar`` (the default), this collection will be used as a
# standard calendar, that is, only files with the ``.ics`` extension will be
# considered, all other files are ignored (except for a possible `color` file).
#
# If set to ``birthdays`` khal will expect a VCARD collection and extract
# birthdays from those VCARDS, that is only files with ``.vcf`` extension will
# be considered, all other files will be ignored.  ``birthdays`` also implies
# ``readonly=True``.
#
# If set to ``discover``, khal will use
# `globbing <https://en.wikipedia.org/wiki/Glob_(programming)>`_ to expand this
# calendar's `path` to (possibly) several paths and use those as individual
# calendars (this cannot be used with `birthday` collections`). See `Exemplary
# discover usage`_ for an example.
#
# If an individual calendar vdir has a `color` file, the calendar's color will
# be set to the one specified in the `color` file, otherwise the color from the
# *calendars* subsection will be used.
type = option('calendar', 'birthdays', 'discover', default='calendar')

# All email addresses associated with this account, separated by commas.
# For now it is only used to check what participation status ("PARTSTAT")
# belongs to the user.
addresses = force_list(default='')

[sqlite]
# khal stores its internal caching database here, by default this will be in the *$XDG_CACHE_HOME/khal/khal.db* (this will most likely be *~/.cache/khal/khal.db*).
path = expand_db_path(default=None)

# It is mandatory to set (long)date-, time-, and datetimeformat options, all others options in the **[locale]** section are optional and have (sensible) defaults.
[locale]

# the first day of the week, where Monday is 0 and Sunday is 6
firstweekday = integer(0, 6, default=0)

# by default khal uses some unicode symbols (as in 'non-ascii') as indicators for things like repeating events,
# if your font, encoding etc. does not support those symbols, set this to *False* (this will enable ascii based replacements).
unicode_symbols = boolean(default=True)

# this timezone will be used for new events (when no timezone is specified) and
# when khal does not understand the timezone specified in the icalendar file.
# If no timezone is set, the timezone your computer is set to will be used.
default_timezone = timezone(default=None)

# khal will show all times in this timezone
# If no timezone is set, the timezone your computer is set to will be used.
local_timezone = timezone(default=None)

# khal will display and understand all times in this format.

# The formatting string is interpreted as defined by Python's `strftime
# <https://docs.python.org/3/library/time.html#time.strftime>`_, which is
# similar to the format specified in ``man strftime``.

# In the configuration file it may be necessary to enclose the format in
# quotation marks to force it to be loaded as a string.
timeformat = string(default='%X')

# khal will display and understand all dates in this format, see :ref:`timeformat <locale-timeformat>` for the format
dateformat = string(default='%x')

# khal will display and understand all dates in this format, it should
# contain a year (e.g. *%Y*) see :ref:`timeformat <locale-timeformat>` for the format.
longdateformat = string(default='%x')

# khal will display and understand all datetimes in this format, see
# :ref:`timeformat <locale-timeformat>` for the format.
datetimeformat = string(default='%c')

# khal will display and understand all datetimes in this format, it should
# contain a year (e.g. *%Y*) see :ref:`timeformat <locale-timeformat>` for the format.
longdatetimeformat = string(default='%c')


# Enable weeknumbers in `calendar` and `interactive` (ikhal) mode by specifying
# whether they should be displayed on the 'left' or 'right'. These are iso
# weeknumbers, so will only work properly if `firstweekday` is set to 0
weeknumbers = weeknumbers(default='off')

# Keybindings for :command:`ikhal` are set here. You can bind more than one key
# (combination) to a command by supplying a comma-separated list of keys.
# For binding key combinations concatenate them keys (with a space in
# between), e.g. **ctrl n**.
[keybindings]

# move the cursor up (in the calendar browser)
up = force_list(default=list('up', 'k'))

# move the cursor down (in the calendar browser)
down = force_list(default=list('down', 'j'))

# move the cursor right (in the calendar browser)
right = force_list(default=list('right', 'l', ' '))

# move the cursor left (in the calendar browser)
left = force_list(default=list('left', 'h', 'backspace'))

# create a new event on the selected date
new = force_list(default=list('n'))

# delete the currently selected event
delete = force_list(default=list('d'))

# show details or edit (if details are already shown) the currently selected event
view = force_list(default=list('enter'))

# edit the currently selected events' raw .ics file with $EDITOR
# Only use this, if you know what you are doing, the icalendar library we use
# doesn't do a lot of validation, it silently disregards most invalid data.
external_edit = force_list(default=list('meta E'))

# focus the calendar browser on today
today = force_list(default=list('t'))

# save the currently edited event and leave the event editor
save = force_list(default=list('meta enter'))

# duplicate the currently selected event
duplicate = force_list(default=list('p'))

# export event as a .ics file
export = force_list(default=list('e'))

# go into highlight (visual) mode to choose a date range
mark = force_list(default=list('v'))

# in highlight mode go to the other end of the highlighted date range
other = force_list(default=list('o'))

# open a text field to start a search for events
search = force_list(default=list('/'))

# show logged messages
log = force_list(default=list('L'))

# cycle through the available views of ikhal's right column (the default event
# list and any views supplied by plugins)
switch_view = force_list(default=list('w'))

# the same day in the next/previous month (or the month's last day), in the
# month column, the list and the views of the right column
next_month = force_list(default=list('}'))
prev_month = force_list(default=list('{'))

# the same day in the next/previous year
next_year = force_list(default=list(']'))
prev_year = force_list(default=list('['))

# go to a date typed at the bottom: dates as on khal's command line (in the
# configured formats, ISO, weekday names, today, tomorrow), or relative like
# +3d, -2w, +1m, -1y
goto_date = force_list(default=list('g'))

# remove all deletion marks (events marked with `delete` are only deleted when
# ikhal quits)
undo_all_deletions = force_list(default=list('U'))

# while editing an event: the next view of the right column, without leaving
# the editor
switch_view_editor = force_list(default=list('meta w'))

# while editing an event: move the focus between the editor and the right
# column (the events, where the view's own keys work, e.g. `switch_view`)
other_column = force_list(default=list('f6'))

# while editing an event: move the border between the editor and the right
# column (it can also be dragged with the mouse), kept for the session
editor_narrower = force_list(default=list('meta <'))
editor_wider = force_list(default=list('meta >'))

# quit
quit = force_list(default=list('q', 'Q'))


# Some default values and behaviors are set here.
[default]

# The calendar to use if none is specified for some operation (e.g. if adding a
# new event). If this is not set, such operations require an explicit value.
default_calendar = string(default=None)

# By default, khal displays only dates with events in `list` or `calendar`
# view.  Setting this to *True* will show all days, even when there is no event
# scheduled on that day.
show_all_days = boolean(default=False)

# After adding a new event, what should be printed to standard out? The whole
# event in text form, the path to where the event is now saved or nothing?
print_new = option('event', 'path', 'False', default=False)

# If true, khal will highlight days with events. Options for
# highlighting are in [highlight_days] section.
highlight_event_days = boolean(default=False)

# Controls for how many days into the future we show events (for example, in
# `khal list`) by default.
timedelta = timedelta(default='2d')


# Define the default duration for an event ('khal new' only)
default_event_duration = timedelta(default='1h')

# Define the defaut duration for a day-long event ('khal new' only)
default_dayevent_duration = timedelta(default='1d')

# Define the default alarm for new events, e.g. '15m'
default_event_alarm = timedelta(default='')

# Define the default alarm for new all dayevents, e.g. '12h'
default_dayevent_alarm = timedelta(default='')

# Whether the mouse should be enabled in interactive mode ('khal interactive' and
# 'ikhal' only)
enable_mouse = boolean(default=True)


# The view section contains configuration options that effect the visual appearance
# when using khal and ikhal.

[view]

# Defines the behaviour of ikhal's right column. If `True`, the right column
# will show events for as many days as fit, moving the cursor through the list
# will also select the appropriate day in the calendar column on the left. If
# `False`, only a fixed ([default] timedelta) amount of days' events will be
# shown, moving through events will not change the focus in the left column.
dynamic_days = boolean(default=True)

# weighting that is applied to the event view window
event_view_weighting = integer(default=1)

# Set to true to always show the event view window when looking at the event list
# (below the list, `event_view_weighting` sets its height relative to the
# list). Otherwise the `view` key (enter) opens the event's details as a card
# right under its row in the list (esc closes it) or, on screens at least
# `event_view_column_from` columns wide, in a column of their own next to the
# list, which follows the focused event. Views of plugins (e.g. a time grid)
# always show the details below themselves.
event_view_always_visible = boolean(default=False)

# Minimum width of the screen (in columns) for showing an event's details in
# a column of their own next to the list of events; 0 never does.
event_view_column_from = integer(default=140, min=0)

# The view used for ikhal's right column on startup. `list` is the built-in
# list of events, plugins can provide additional views (e.g. a time grid where
# the height of an event is proportional to its duration). Press the
# `switch_view` key to cycle through all available views.
default_view = string(default='list')

# Add a blank line before the name of the day (khal only)
blank_line_before_day = boolean(default=False)

# Choose a color theme for khal.
#
# Khal ships with the color themes *dark* and *light* (which use the
# terminal's colours) and *retrobox*, *retrobox-light* (the colours of Vim's
# retrobox, after gruvbox), *ink*, *fjord*, *ember* and *paper* (which bring
# their own background).  Additionally, plugins might supply different color
# schemes.
# You can also define your own color theme in the [palette] section.
theme = string(default='dark')

# Whether to show a visible frame (with *box drawing* characters) around some
# (groups of) elements or not. There are currently several different frame
# options available, that should visually differentiate whether an element is
# in focus or not. Some of them will probably be removed in future releases of
# khal, so please try them out and give feedback on which style you prefer
# (the color of all variants can be defined in the color themes).
frame = option('False', 'width', 'color', 'top', default='False')

# How ikhal's event editor arranges its fields.
#
# *sections* groups the fields under the headings When, Details and Alarms,
# empty fields show a dimmed placeholder.
# *headline* shows the title as a headline with a plain-language summary
# below it and uses short labels (when, where, who, ...); empty optional
# fields are collapsed into a single "+ location  + attendees ..." row.
# *cards* puts each group of fields into its own box, the box containing the
# focus is highlighted.
# *compact* uses one row per field and no blank rows, for narrow panes and
# 80x24 terminals, *compact-ascii* is the same without any non-ASCII
# characters.
# *auto* uses *compact* if the editor is narrow, *sections* otherwise (with
# more spacing on wide screens) and switches when the terminal is resized.
editor_layout = option('auto', 'sections', 'headline', 'cards', 'compact', 'compact-ascii', default='auto')

# An explicitly chosen `editor_layout` falls back to *compact* while the editor
# is narrower than this many columns (and switches back when it gets wider);
# 0 never falls back.
editor_compact_below = integer(default=60, min=0)

# Width of the editor in ikhal's editing screen, the rest is for the events at
# its right: empty for automatic (two thirds, at most 94 columns), a
# percentage (`60%`) or a number of columns. The border can also be moved with
# the mouse or the `editor_narrower`/`editor_wider` keys.
editor_width = string(default='')

# What happens to the screen behind floating boxes (dialogs, help, log) in
# ikhal: *grey* draws it in faded greys (on terminals with 16 colours only: in
# dark grey) so only the box keeps its colours, *none* leaves it as it is.
backdrop = option('grey', 'none', default='grey')

# How ikhal's month column marks days with events: *calendar* colours the
# day's number in the colour of (the first of) its calendars (only with
# `[default] highlight_event_days`, see `[highlight_days]`), *dot* keeps the
# number in the normal colour and puts a coloured • after it (‥ if there are
# events from several calendars), *heat* tints the day's background by how busy
# it is (three levels, from the theme's accent colour), *none* marks nothing.
# Today and marked ranges always keep their own style.
day_marking = option('calendar', 'dot', 'heat', 'none', default='calendar')

# Step (in minutes) of the minutes column of the time picker in ikhal's event
# editor (enter on a time).
minute_step = integer(default=5, min=1, max=30)

# How dense ikhal's list of events is. The densities are presets of the format
# of events and day headers: *comfortable* (a second row per event with
# calendar · location · repeat/alarm), *regular* (one row per event, day
# headers as rules), *dense* (no day header rows, the day stands in front of
# the day's first event); *auto* picks the airiest of these that still shows
# the next `density_min_days` days completely. *classic* uses
# `agenda_event_format` and the old day headers.
density = option('auto', 'comfortable', 'regular', 'dense', 'classic', default='auto')

# Number of days `density = auto` tries to show completely.
density_min_days = integer(default=3, min=1)

# How events in ikhal's list show their calendar's colour: *line* colours the
# whole line, *bar* only a ▍ in front of the event (the text stays in the
# normal colour).
event_color = option('line', 'bar', default='bar')

# Show free time between two timed events of the same day in ikhal's list
# ("┊ 4h free") if it is at least this long; `0` or `off` disables it.
show_free_time = string(default='3h')

# Only count free time within these hours, e.g. `08:00-18:00` (default: the
# whole time between two events counts).
free_time_hours = string(default='')

# Format of the day headers in ikhal's list (empty: the density's default,
# or "Today (Thursday, 26.11.2026)" with `density = classic`). Available:
# {name}, {name-short}, {day}, {day-padded} (single-digit days with a leading
# space, so consecutive headers line up), {month}, {month-short}, {date},
# {date-long}, {week}, {relative} (today, tomorrow, yesterday or empty) and
# {relative-separator} (" · " if there is a relative day).
ikhal_day_format = string(default='')

# With `density = classic`: draw the day headers as plain text or as a rule
# (`── Fr 27 Nov · tomorrow ─────`).
day_header = option('text', 'rule', default='text')

# Format of ikhal's header line (empty: the title of the current pane).
# Available: {weekday}, {day}, {month-short}, {date}, {date-long}, {time},
# {week}, and of the next event: {next-title}, {next-in} (e.g. "in 1h10m"),
# {next-time} and {next-separator} ("  next: " if there is a next event).
header_format = string(default='{weekday} {day} {month-short} {time}{next-separator}{next-title} {next-in}')

# Whether to use bold text for light colors or not. Non-bold light colors may
# not work on all terminals but allow using light background colors.
bold_for_light_color = boolean(default=True)

# Default formatting for events used when the user asks for all events in a
# given time range, used for :command:`list`, :command:`calendar` and in
# :command:`interactive` (ikhal). Please note, that any color styling will be
# ignored in `ikhal`, where events will always be shown in the color of the
# calendar they belong to.
# The syntax is the same as for :option:`--format`.
agenda_event_format = string(default='{calendar-color}{cancelled}{start-end-time-style} {title}{repeat-symbol}{alarm-symbol}{description-separator}{description}{reset}')

# Specifies how each *day header* is formatted.
agenda_day_format = string(default='{bold}{name}, {date-long}{reset}')

# Display month name on row when the week contains the first day
# of the month ('firstday') or when the first day of the week is in the
# month ('firstfullweek')
monthdisplay = monthdisplay(default='firstday')

# Default formatting for events used when the start- and end-date are not
# clear through context, e.g. for :command:`search`, used almost everywhere
# but :command:`list` and :command:`calendar`. It is therefore probably a
# sensible choice to include the start- and end-date.
# The syntax is the same as for :option:`--format`.
event_format = string(default='{calendar-color}{cancelled}{start}-{end} {title}{repeat-symbol}{alarm-symbol}{description-separator}{description}{reset}')

# Minimum number of months displayed by calendar command
# default is 3 months
min_calendar_display = integer(default=3)

# When highlight_event_days is enabled, this section specifies how
# the highlighting/coloring of days is handled.
[highlight_days]

# Highlighting method to use -- foreground or background
method = option('foreground', 'fg', 'background', 'bg', default='fg')

# What color to use when highlighting -- explicit color or use calendar
# color when set to ''
color = color(default='')

# How to color days with events from multiple calendars -- either
# explicit color or use calendars' colors when set to ''
multiple = color(default='')

# When `multiple` is set to a specific color, setting this to *True* will
# cause khal to use that color only for days with events from 3 or more
# calendars (hence preserving the two-color-highlight for days where all
# calendar colors can be displayed)
multiple_on_overflow = boolean(default=False)

# Default color for calendars without color -- when set to '' it
# actually disables highlighting for events that should use the
# default color.
default_color = color(default='')

# Override ikhal's color theme with a custom palette. This is useful to style
# certain elements of ikhal individually.
# Palette entries take the form of `key = foreground, background, mono,
# foreground_high, background_high` where foreground and background are used in
# "low color mode"  and foreground_high and background_high are used in "high
# color mode" and mono if only monocolor is supported. If you don't want to set
# a value for a certain color, use an empty string (`''`).
# Valid entries for low color mode are listed on the `urwid website
# <http://urwid.org/manual/displayattributes.html#standard-foreground-colors>`_. For
# high color mode you can use any valid 24-bit color value, e.g. `'#ff0000'`.
#
# .. note::
#     24-bit colors must be enclosed in single quotes to be parsed correctly,
#     otherwise the `#` will be interpreted as a comment.
#
# Most modern terminals should support high color mode.
#
# Example entry (particular ugly):
#
# .. highlight:: ini
#
# ::
#
#  [palette]
#  header = light red, default, default, '#ff0000', default
#  edit = '', '', 'bold', '#FF00FF', '#12FF14'
#  footer = '', '', '', '#121233', '#656599'
#
# See the default palettes in `khal/ui/colors.py` for all available keys.
# If you can't theme an element in ikhal, please open an issue on `github
# <https://github.com/pimutils/khal/issues/new/choose>`_.
[palette]


# Plugins may read their settings from subsections of this section, e.g.
# ``[[timegrid]]``. Its contents are not validated by khal.
[plugins]
