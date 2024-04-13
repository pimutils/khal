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
# khal stores its internal caching database here, by default this will be in the *$XDG_DATA_HOME/khal/khal.db* (this will most likely be *~/.local/share/khal/khal.db*).
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
event_view_always_visible = boolean(default=False)

# Add a blank line before the name of the day (khal only)
blank_line_before_day = boolean(default=False)

# Choose a color theme for khal.
#
# Khal ships with two color themes, *dark* and *light*.  Additionally, plugins
# might supply different color schemes.
# You can also define your own color theme in the [palette] section.
theme = string(default='dark')

# Whether to show a visible frame (with *box drawing* characters) around some
# (groups of) elements or not. There are currently several different frame
# options available, that should visually differentiate whether an element is
# in focus or not. Some of them will probably be removed in future releases of
# khal, so please try them out and give feedback on which style you prefer
# (the color of all variants can be defined in the color themes).
frame = option('False', 'width', 'color', 'top', default='False')

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
