
The [calendars] section
~~~~~~~~~~~~~~~~~~~~~~~

The *[calendars]* is mandatory and must contain at least one subsection.
Every subsection must have a unique name (enclosed by two square brackets).
Each subection needs exactly one *path* setting, everything else is optional.
Here is a small example:

.. literalinclude:: ../../tests/configs/small.conf
 :language: ini

.. _calendars-color:

.. object:: color

    
    khal will use this color for coloring this calendar's event. Depending on
    your terminal emulator's settings, they might look different than what their
    name implies.

      :type: option, allowed values are *black*, *white*, *brown*, *yellow*, *dark grey*, *dark green*, *dark blue*, *light grey*, *light green*, *light blue*, *dark magenta*, *dark cyan*, *dark red*, *light magenta*, *light cyan*, *light red* and **
      :default: 

.. _calendars-path:

.. object:: path

    the path to a *vdir* where this calendar is saved

      :type: string
      :default: None

.. _calendars-readonly:

.. object:: readonly

    
    setting this to *True*, will keep khal from making any changes to this
    calendar

      :type: boolean
      :default: False

The [sqlite] section
~~~~~~~~~~~~~~~~~~~~


.. _sqlite-path:

.. object:: path

    khal stores its internal caching database here, by default this will be in the *$XDG_DATA_HOME/khal/khal.db* (this will most likely be *~/.local/share/khal/khal.db*).

      :type: string
      :default: None

The [locale] section
~~~~~~~~~~~~~~~~~~~~

The most important options in the the **[locale]** section are probably (long-)time and dateformat.

.. _locale-encoding:

.. object:: encoding

    
    set this to the encoding of your terminal emulator

      :type: string
      :default: utf-8

.. _locale-local_timezone:

.. object:: local_timezone

    
    khal will show all times in this timezone
    If no timezone is set, the timezone your computer is set to will be used.

      :type: timezone
      :default: None

.. _locale-unicode_symbols:

.. object:: unicode_symbols

    
    by default khal uses some unicode symbols (as in 'non-ascii') as indicators for things like repeating events,
    if your font, encoding etc. does not support those symbols, set this to *False* (this will enable ascii based replacements).

      :type: boolean
      :default: True

.. _locale-longdateformat:

.. object:: longdateformat

    
    khal will display and understand all dates in this format, it should
    contain a year (e.g. *%Y*) see :ref:`timeformat <locale-timeformat>` for the format.

      :type: string
      :default: %d.%m.%Y

.. _locale-longdatetimeformat:

.. object:: longdatetimeformat

    
    khal will display and understand all datetimes in this format, it should
    contain a year (e.g. *%Y*) see :ref:`timeformat <locale-timeformat>` for the format.

      :type: string
      :default: %d.%m.%Y %H:%M

.. _locale-default_timezone:

.. object:: default_timezone

    
    this timezone will be used for new events (when no timezone is specified) and
    when khal does not understand the timezone specified in the icalendar file.
    If no timezone is set, the timezone your computer is set to will be used.

      :type: timezone
      :default: None

.. _locale-datetimeformat:

.. object:: datetimeformat

    
    khal will display and understand all datetimes in this format, see
    :ref:`timeformat <locale-timeformat>` for the format.

      :type: string
      :default: %d.%m. %H:%M

.. _locale-weeknumbers:

.. object:: weeknumbers

    
    
    Enable weeknumbers in `calendar` and `interactive` (ikhal) mode. As those are
    iso weeknumbers, they only work properly if `firstweekday` is set to 0

      :type: weeknumbers
      :default: off

.. _locale-timeformat:

.. object:: timeformat

    
    khal will display and understand all times in this format, use the standard
    format as understood by strftime, see https://strftime.net or :command:`man strftime`

      :type: string
      :default: %H:%M

.. _locale-dateformat:

.. object:: dateformat

    
    khal will display and understand all dates in this format, see :ref:`timeformat <locale-timeformat>` for the format

      :type: string
      :default: %d.%m.

.. _locale-firstweekday:

.. object:: firstweekday

    
    the day first day of the week, were Monday is 0 and Sunday is 6

      :type: integer, allowed values are between 0 and 6
      :default: 0

The [default] section
~~~~~~~~~~~~~~~~~~~~~

The default section begins with a **[default]** tag. Some default values and
behaviours are set here.

.. _default-default_calendar:

.. object:: default_calendar

    
    the calendar to use if no one is specified but only one can be used (e.g. if
    adding a new event), this should be a valid calendar name.

      :type: string
      :default: None

.. _default-default_command:

.. object:: default_command

    
    command to be executed if no command is given when executing khal
    this is a rather important subcommand

      :type: option, allowed values are *calendar*, *agenda* and *interactive*
      :default: calendar

.. _default-show_all_days:

.. object:: show_all_days

    by default, khal does not show days without event in calendar and
    agenda displays. Setting this to True makes khal show all days.

      :type: boolean
      :default: False
