import click
import pytest

from khal.configwizard import validate_int


def test_validate_int():
    assert validate_int('3', 0, 3) == 3
    with pytest.raises(click.UsageError):
        validate_int('3', 0, 2)
    with pytest.raises(click.UsageError):
        validate_int('two', 0, 2)
