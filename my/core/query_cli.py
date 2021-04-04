import re
from datetime import date, datetime, timedelta
from typing import Callable, Iterator, Union

from .query import QueryException, select

DateLike = Union[datetime, date]

timedelta_regex = re.compile(r"^((?P<weeks>[\.\d]+?)w)?((?P<days>[\.\d]+?)d)?((?P<hours>[\.\d]+?)h)?((?P<minutes>[\.\d]+?)m)?((?P<seconds>[\.\d]+?)s)?$")


# https://stackoverflow.com/a/51916936
def parse_timedelta_string(timedelta_str: str) -> timedelta:
    """
    This uses a syntax similar to the 'GNU sleep' command
    e.g.: 1w5d5h10m50s means '1 week, 5 days, 5 hours, 10 minutes, 50 seconds'
    """
    parts = timedelta_regex.match(timedelta_str)
    if parts is None:
        raise ValueError(f"Could not parse time duration from {timedelta_str}.\nValid examples: '8h', '1w2d8h5m20s', '2m4s'")
    time_params = {name: float(param) for name, param in parts.groupdict().items() if param}
    return timedelta(**time_params)  # type: ignore[arg-type]


def test_parse_timedelta_string():

    import pytest

    with pytest.raises(ValueError, match=r"Could not parse time duration from"):
        parse_timedelta_string("5xxx")

    res = parse_timedelta_string("1w5d5h10m50s")
    assert res == timedelta(days=7.0 + 5.0, hours=5.0, minutes=10.0, seconds=50.0)
