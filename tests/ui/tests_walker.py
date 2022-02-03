import datetime as dt

from freezegun import freeze_time

from khal.ui import DayWalker, DListBox, StaticDayWalker

from ..utils import LOCALE_BERLIN
from .canvas_render import CanvasTranslator

CONF = {'locale': LOCALE_BERLIN, 'keybindings': {},
        'view': {'monthdisplay': 'firstday'},
        'default': {'timedelta': dt.timedelta(days=3)},
        }


palette = {
    'date header focused': 'blue',
    'date header': 'green',
    'default': 'black',
}


@freeze_time('2017-6-7')
def test_daywalker(coll_vdirs):
    collection, _ = coll_vdirs
    this_date = dt.date.today()
    daywalker = DayWalker(this_date, None, CONF, collection, delete_status={})
    elistbox = DListBox(
        daywalker, parent=None, conf=CONF,
        delete_status=lambda: False,
        toggle_delete_all=None,
        toggle_delete_instance=None,
        dynamic_days=True,
    )
    canvas = elistbox.render((50, 6), True)
    assert CanvasTranslator(canvas, palette).transform() == \
        """\x1b[34mToday (Wednesday, 07.06.2017)\x1b[0m
\x1b[32mTomorrow (Thursday, 08.06.2017)\x1b[0m
\x1b[32mFriday, 09.06.2017 (2 days from now)\x1b[0m
\x1b[32mSaturday, 10.06.2017 (3 days from now)\x1b[0m
\x1b[32mSunday, 11.06.2017 (4 days from now)\x1b[0m
\x1b[32mMonday, 12.06.2017 (5 days from now)\x1b[0m
"""


@freeze_time('2017-6-7')
def test_staticdaywalker(coll_vdirs):
    collection, _ = coll_vdirs
    this_date = dt.date.today()
    daywalker = StaticDayWalker(this_date, None, CONF, collection, delete_status={})
    elistbox = DListBox(
        daywalker, parent=None, conf=CONF,
        delete_status=lambda: False,
        toggle_delete_all=None,
        toggle_delete_instance=None,
        dynamic_days=False,
    )
    canvas = elistbox.render((50, 10), True)
    assert CanvasTranslator(canvas, palette).transform() == \
        """\x1b[34mToday (Wednesday, 07.06.2017)\x1b[0m
\x1b[32mTomorrow (Thursday, 08.06.2017)\x1b[0m
\x1b[32mFriday, 09.06.2017 (2 days from now)\x1b[0m







"""


@freeze_time('2017-6-7')
def test_staticdaywalker_3(coll_vdirs):
    collection, _ = coll_vdirs
    this_date = dt.date.today()
    conf = {}
    conf.update(CONF)
    conf['default'] = {'timedelta': dt.timedelta(days=1)}
    daywalker = StaticDayWalker(this_date, None, conf, collection, delete_status={})
    elistbox = DListBox(
        daywalker, parent=None, conf=conf,
        delete_status=lambda: False,
        toggle_delete_all=None,
        toggle_delete_instance=None,
        dynamic_days=False,
    )
    canvas = elistbox.render((50, 10), True)
    assert CanvasTranslator(canvas, palette).transform() == \
        '\x1b[34mToday (Wednesday, 07.06.2017)\x1b[0m\n\n\n\n\n\n\n\n\n\n'
