from pathlib import Path

import pytest # type: ignore

from my.calendar.holidays import is_holiday


def test() -> None:
    assert is_holiday('20190101')
    assert not is_holiday('20180601')
    assert is_holiday('20200906') # national holiday in Bulgaria


@pytest.fixture(autouse=True)
def prepare(tmp_path: Path):
    from . import tz
    # todo meh. fixtures can't be called directly?
    orig = tz.prepare.__wrapped__ # type: ignore
    yield from orig(tmp_path)
