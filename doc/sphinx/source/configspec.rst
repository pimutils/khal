
The [calendars] section
~~~~~~~~~~~~~~~~~~~~~~~

The only non-optional section is the *[calendars]* section, which must
contain at least one subsection. Every subsection must start with a unique
name enclosed by two square brackets. Each section needs exactly one *path*
setting, everything else is optional. Here is a small example:

.. literalinclude:: ../../../tests/configs/small.conf
    :language: ini

.. object:: color

    
    khal will use this color for coloring this calendar's event. Depending on
    your terminal emulator's settings, they might look different than what their
    name implies.
     :type: option, allowed values are *black*, *white*, *brown*, *yellow*, *dark grey*, *dark green*, *dark blue*, *light grey*, *light green*, *light blue*, *dark magenta*, *dark cyan*, *dark red*, *light magenta*, *light cyan* and *light red*
     :default: None

.. object:: path

    the path to a *vdir* where this calendar is saved
     :type: string
     :default: None

.. object:: readonly

    
    setting this to *True*, will keep khal from making any changes to this
    calendar
     :type: boolean
     :default: False

The [locale] section
~~~~~~~~~~~~~~~~~~~~

The most important options in the the **[locale]** section are probably (long-)time and dateformat.

.. object:: encoding

    
    set this to the encoding of your terminal emulator
     :type: string
     :default: utf-8

.. object:: local_timezone

    
    khal will show all times in this timezone
     :type: timezone
     :default: None

.. object:: unicode_symbols

    
    by default khal uses some unicode symbols (as in 'non-ascii') as indicators for things like repeating events,
    if your font, encoding etc. does not support those symbols, set this to *False* (this will enable ascii based replacements).
     :type: boolean
     :default: True

.. object:: longdateformat

    
    khal will display and understand all dates in this format, it should
    contain a year (e.g. *%Y*) see :ref:`timeformat` for the format.
     :type: string
     :default: %d.%m.%Y

.. object:: longdatetimeformat

    
    khal will display and understand all datetimes in this format, it should
    contain a year (e.g. *%Y*) see :ref:`timeformat` for the format.
     :type: string
     :default: %d.%m.%Y %H:%M

.. object:: default_timezone

    
    this timezone will be used for new events (when no timezone is specified) and
    when khal does not understand the timezone specified in the icalendar file
     :type: timezone
     :default: None

.. object:: datetimeformat

    
    khal will display and understand all datetimes in this format, see
    :ref:`timeformat` for the format.
     :type: string
     :default: %d.%m. %H:%M

.. object:: timeformat

    
    khal will display and understand all times in this format, use the standard
    format as understood by strftime, see https://strftime.net or :command:`man strftime`
     :type: string
     :default: %H:%M

.. object:: dateformat

    
    khal will display and understand all dates in this format, see :ref:`timeformat` for the format
     :type: string
     :default: %d.%m.

.. object:: firstweekday

    
    the day first day of the week, were Monday is 0 and Sunday is 6
     :type: integer, allowed values are between 0 and 6
     :default: 0

The [default] section
~~~~~~~~~~~~~~~~~~~~~


The default section begins with a **[default]** tag. Some default values and
behaviours are set here.

.. object:: debug

    
    whether to print debugging information or not
     :type: boolean
     :default: False

.. object:: default_calendar

    
    the calendar to use if no one is specified but only one can be used (e.g. if
    adding a new event), this should be a valid calendar name.
     :type: string
     :default: None

.. object:: default_command

    
    command to be executed if no command is given when executing khal
    this is a rather important subcommand
     :type: option, allowed values are *calendar*, *agenda* and *interactive*
     :default: calendar
