from my.calendar.holidays import is_holiday


def test() -> None:
    assert is_holiday('20190101')
    assert not is_holiday('20180601')
