[calendars]
# The *[calendars]* is mandatory and must contain at least one subsection.
# Every subsection must have a unique name (enclosed by two square brackets).
# Each subection needs exactly one *path* setting, everything else is optional.
# Here is a small example:
#
# .. literalinclude:: ../../tests/configs/small.conf
#  :language: ini
[[__many__]]
# the path to a *vdir* where this calendar is saved
path = expand_path(default=None)

# khal will use this color for coloring this calendar's event. Depending on
# your terminal emulator's settings, they might look different than what their
# name implies.
color = option('black', 'white', 'brown', 'yellow','dark grey', 'dark green', 'dark blue','light grey', 'light green', 'light blue','dark magenta', 'dark cyan', 'dark red','light magenta', 'light cyan', 'light red', '', default='')

# setting this to *True*, will keep khal from making any changes to this
# calendar
readonly = boolean(default=False)

# Set the type of this collection, the default is ``calendar``.
# If set to ``birthdays`` khal will expect a VCARD collection and extract
# birthdays from those VCARDS. ``birthdays`` also implies ``readonly=True``.
type = option('calendar', 'birthdays', default='calendar')

[sqlite]
# khal stores its internal caching database here, by default this will be in the *$XDG_DATA_HOME/khal/khal.db* (this will most likely be *~/.local/share/khal/khal.db*).
path = expand_db_path(default=None)

# The most important options in the the **[locale]** section are probably (long-)time and dateformat.
[locale]

# set this to the encoding of your terminal emulator
encoding = string(default='utf-8')

# the day first day of the week, were Monday is 0 and Sunday is 6
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
# <https://docs.python.org/2/library/time.html#time.strftime>`_, which is
# similar to the format specified in ``man strftime``.
timeformat = string(default='%H:%M')

# khal will display and understand all dates in this format, see :ref:`timeformat <locale-timeformat>` for the format
dateformat = string(default='%d.%m.')

# khal will display and understand all dates in this format, it should
# contain a year (e.g. *%Y*) see :ref:`timeformat <locale-timeformat>` for the format.
longdateformat = string(default='%d.%m.%Y')

# khal will display and understand all datetimes in this format, see
# :ref:`timeformat <locale-timeformat>` for the format.
datetimeformat = string(default='%d.%m. %H:%M')

# khal will display and understand all datetimes in this format, it should
# contain a year (e.g. *%Y*) see :ref:`timeformat <locale-timeformat>` for the format.
longdatetimeformat = string(default='%d.%m.%Y %H:%M')


# Enable weeknumbers in `calendar` and `interactive` (ikhal) mode. As those are
# iso weeknumbers, they only work properly if `firstweekday` is set to 0
weeknumbers = weeknumbers(default='off')

# keybindings for :command:`ikhal` are set here. You can bind more than one key
# (combination) to a command by supplying a comma-seperated list of keys.
# For binding key combinations just add concatenate them (with a space in
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
view = force_list(default=list('enter', 'tab'))

# focus the calendar browser on today
today = force_list(default=list('t'))

# save the currently edited event and leave the event editor
save = force_list(default=list('meta enter'))

# duplicate the currently selected event
duplicate = force_list(default=list('p'))

# The default section begins with a **[default]** tag. Some default values and
# behaviours are set here.
[default]

# command to be executed if no command is given when executing khal
default_command = option('calendar', 'agenda', 'interactive', 'printformats', 'printcalendars', '', default='calendar')

# The calendar to use if none is specified for some operation (e.g. if adding a
# new event). If this is not set, such operations requre an explicit value.
default_calendar = string(default=None)

# By default, khal displays only dates with event in "agenda" view.
# Setting this to *True* will show all days in "agenda", even
# when there is no event
show_all_days = boolean(default=False)

# By default, khal show events for today and tomorrow.
# Setting this to a different value will show events of that amount of days by
# defaut.
days = integer(default=2)

# After adding a new event, what should be printed to standard out? The whole
# event in text form, the path to where the event is now saved or nothing?
print_new = option('event', 'path', 'False', default=False)

# If true, khal will highlight days with events. Options for
# highlighting are in [highlight_days] section.
highlight_event_days = boolean(default=False)

# The view section contains config options that effect the visual appearance
# when using ikhal
[view]

# This is the weighting that is applied to the event view window
event_view_weighting = integer(default=1)

# Set to true to always show the event view window when looking at the event list
event_view_always_visible = boolean(default=False)

# Choose a color theme for khal.
# 
# This is very much work in progress. Help is really welcome! The two currently
# available color schemes (*dark* and *light*) are defined in
# *khal/ui/themes.py*, you can either help improve those or create a new one
# (see below). As ikhal uses urwid, have a look at `urwid's documentation`__
# for how to set colors and/or at the existing schemes. If you cannot change
# the color of an element (or have any other problems) please open an issue on
# github_.
#
# If you want to create your own color scheme, just copy the structure of the
# existing ones, give it a new and unique name and also add it as an option in
# `khal/settings/khal.spec` in the section `[default]` of the property `theme`.
#
# __ http://urwid.org/manual/displayattributes.html
# .. _github: # https://github.com/geier/khal/issues
theme = option('dark', 'light', default='dark')

# Whether to show a visible frame (with *box drawing* characters) around some
# (groups of) elements.
frame = boolean(default=False)

# When highlight_event_days is enabled, this section specifies how is
# the highlighting rendered.
[highlight_days]

# Highlighting method to use - foreground or background
method = option('foreground', 'fg', 'background', 'bg', default='fg')

# What color to use when highlighting - explicit color or use calendar
# color when set to ''
color = option('black', 'white', 'brown', 'yellow','dark grey', 'dark green', 'dark blue','light grey', 'light green', 'light blue','dark magenta', 'dark cyan', 'dark red','light magenta', 'light cyan', 'light red', '', default='')

# How to color days with events from multiple calendars - either
# explicit color or use calendars' colors when set to ''
multiple = option('black', 'white', 'brown', 'yellow','dark grey', 'dark green', 'dark blue','light grey', 'light green', 'light blue','dark magenta', 'dark cyan', 'dark red','light magenta', 'light cyan', 'light red', '', default='')

# Default color for calendars without color - when se to '' it
# actually disables highlighting for events that should use the
# default color.
default_color = option('black', 'white', 'brown', 'yellow','dark grey', 'dark green', 'dark blue','light grey', 'light green', 'light blue','dark magenta', 'dark cyan', 'dark red','light magenta', 'light cyan', 'light red', '', default='')
