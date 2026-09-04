from datetime import date, datetime, timedelta, timezone
from typing import assert_type

import pytest

from my.calendar.holidays import DateIsh, as_date, is_holiday
from my.core.datetime import Date

from .shared_tz_config import config  # noqa: F401  # autoused fixture


@pytest.mark.parametrize(
    'value',
    [
        date(2024, 6, 3),
        datetime(2024, 6, 3, 12),
        datetime(2024, 6, 3, 23, tzinfo=timezone(timedelta(hours=-5))),
        '20240603',
    ],
)
def test_as_date(value: DateIsh) -> None:
    result = as_date(value)
    assert_type(result, Date)
    assert type(result) is date
    assert result == date(2024, 6, 3)
    if type(value) is date:
        assert result is value


def test_as_date_invalid_string() -> None:
    with pytest.raises(ValueError):
        as_date('not a date')


def test_is_holiday() -> None:
    assert is_holiday('20190101')
    assert not is_holiday('20180601')
    assert is_holiday('20200906')  # national holiday in Bulgaria
