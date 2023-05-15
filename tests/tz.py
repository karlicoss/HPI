import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest
import pytz

from my.core.error import notnone

import my.time.tz.main as TZ
import my.time.tz.via_location as LTZ


def test_iter_tzs() -> None:
    ll = list(LTZ._iter_tzs())
    assert len(ll) > 3


def test_past() -> None:
    # should fallback to the home location provider
    dt = D('20000101 12:34:45')
    dt = TZ.localize(dt)
    tz = dt.tzinfo
    assert tz is not None
    assert getattr(tz, 'zone') == 'America/New_York'


def test_future() -> None:
    fut = datetime.now() + timedelta(days=100)
    # shouldn't crash at least
    assert TZ.localize(fut) is not None


def test_tz() -> None:
    # todo hmm, the way it's implemented at the moment, never returns None?

    # not present in the test data
    tz = LTZ._get_tz(D('20200101 10:00:00'))
    assert notnone(tz).zone == 'Europe/Sofia'

    tz = LTZ._get_tz(D('20170801 11:00:00'))
    assert notnone(tz).zone == 'Europe/Vienna'

    tz = LTZ._get_tz(D('20170730 10:00:00'))
    assert notnone(tz).zone == 'Europe/Rome'

    tz = LTZ._get_tz(D('20201001 14:15:16'))
    assert tz is not None

    on_windows = sys.platform == 'win32'
    if not on_windows:
        tz = LTZ._get_tz(datetime.min)
        assert tz is not None
    else:
        # seems this fails because windows doesn't support same date ranges
        # https://stackoverflow.com/a/41400321/
        with pytest.raises(OSError):
            LTZ._get_tz(datetime.min)


def test_policies() -> None:
    getzone = lambda dt: getattr(dt.tzinfo, 'zone')

    naive = D('20170730 10:00:00')
    # actual timezone at the time
    assert getzone(TZ.localize(naive)) == 'Europe/Rome'

    z = pytz.timezone('America/New_York')
    aware = z.localize(naive)

    assert getzone(TZ.localize(aware)) == 'America/New_York'

    assert getzone(TZ.localize(aware, policy='convert')) == 'Europe/Rome'


    with pytest.raises(RuntimeError):
        assert TZ.localize(aware, policy='throw')


def D(dstr: str) -> datetime:
    return datetime.strptime(dstr, '%Y%m%d %H:%M:%S')



@pytest.fixture(autouse=True)
def prepare(tmp_path: Path):
    from .shared_config import temp_config
    conf = temp_config(tmp_path)

    import my.core.cfg as C
    with C.tmp_config() as config:
        config.google   = conf.google
        config.time     = conf.time
        config.location = conf.location
        yield
