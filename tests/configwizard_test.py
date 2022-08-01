import click
import pytest

from khal.configwizard import get_collection_names_from_vdirs, validate_int


def test_validate_int():
    assert validate_int('3', 0, 3) == 3
    with pytest.raises(click.UsageError):
        validate_int('3', 0, 2)
    with pytest.raises(click.UsageError):
        validate_int('two', 0, 2)


def test_default_vdir(metavdirs):
    names = get_collection_names_from_vdirs([('found', f'{metavdirs}/**/', 'discover')])
    assert names == [
        'my private calendar', 'my calendar', 'public', 'home', 'public1', 'work',
        'cfgcolor', 'cfgcolor_again', 'cfgcolor_once_more', 'dircolor', 'singlecollection',
    ]
