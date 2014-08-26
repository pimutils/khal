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
color = option('black', 'white', 'brown', 'yellow','dark grey', 'dark green', 'dark blue','light grey', 'light green', 'light blue','dark magenta', 'dark cyan', 'dark red','light magenta', 'light cyan', 'light red')

# setting this to *True*, will keep khal from making any changes to this
# calendar
readonly = boolean(default=False)

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

# khal will display and understand all times in this format, use the standard
# format as understood by strftime, see https://strftime.net or :command:`man strftime`
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


# The default section begins with a **[default]** tag. Some default values and
# behaviours are set here.
[default]

# command to be executed if no command is given when executing khal
# this is a rather important subcommand
default_command = option('calendar', 'agenda', 'interactive', default='calendar')

# whether to print debugging information or not
debug = boolean(default=False)

# the calendar to use if no one is specified but only one can be used (e.g. if
# adding a new event), this should be a valid calendar name.
default_calendar = string(default=None)
