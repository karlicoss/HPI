from my.calendar.holidays import is_holiday

from .shared_tz_config import config  # autoused fixture


def test_is_holiday() -> None:
    assert is_holiday('20190101')
    assert not is_holiday('20180601')
    assert is_holiday('20200906')  # national holiday in Bulgaria
