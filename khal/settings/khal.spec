[calendars]
[[__many__]]
path = string(default=None)
color = option('black', 'white', 'brown', 'yellow','dark grey', 'dark green', 'dark blue','light grey', 'light green', 'light blue','dark magenta', 'dark cyan', 'dark red','light magenta', 'light cyan', 'light red')
readonly = boolean(default=False)

[locale]
encoding = string(default='utf-8')
firstweekday = integer(0, 6, default=0)
unicode_symbols = boolean(default=True)
default_timezone = timezone(default=None)
local_timezone = timezone(default=None)
timeformat = string(default='%H:%M')
dateformat = string(default='%d.%m.')
longdateformat = string(default='%d.%m.%Y')
datetimeformat = string(default='%d.%m. %H:%M')
longdatetimeformat = string(default='%d.%m.%Y %H:%M')


[default]
default_command = options('calendar', 'agenda', 'interactive', default='calendar')
debug = boolean(default=False)
default_calendar = string(default=None)
