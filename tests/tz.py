from datetime import datetime, timedelta, date, timezone
from pathlib import Path
import sys

import pytest # type: ignore
import pytz # type: ignore

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

    tz = LTZ._get_tz(datetime.min)
    assert tz is not None


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


# TODO copy pasted from location.py, need to extract some common provider
@pytest.fixture(autouse=True)
def prepare(tmp_path: Path):
    from .common import reset_modules
    reset_modules()

    LTZ._FASTER = True

    from .location import _prepare_google_config
    google = _prepare_google_config(tmp_path)

    class location:
        home = (
            # supports ISO strings
            ('2005-12-04'                                       , (42.697842, 23.325973)), # Bulgaria, Sofia
            # supports date/datetime objects
            (date(year=1980, month=2, day=15)                   , (40.7128  , -74.0060 )), # NY
            # check tz handling..
            (datetime.fromtimestamp(1600000000, tz=timezone.utc), (55.7558  , 37.6173  )), # Moscow, Russia
        )
        # note: order doesn't matter, will be sorted in the data provider

    class time:
        class tz:
            pass # just rely on the default..

    import my.core.cfg as C
    with C.tmp_config() as config:
        config.google   = google
        config.time     = time
        config.location = location
        yield
