import sys
from datetime import datetime, timedelta

import pytest
import pytz

import my.time.tz.main as tz_main
import my.time.tz.via_location as tz_via_location
from my.core import notnone
from my.core.compat import fromisoformat

from .shared_tz_config import config  # autoused fixture


def getzone(dt: datetime) -> str:
    tz = notnone(dt.tzinfo)
    return getattr(tz, 'zone')


@pytest.mark.parametrize('fast', [False, True])
def test_iter_tzs(*, fast: bool, config) -> None:
    # TODO hmm.. maybe need to make sure we start with empty config?
    config.time.tz.via_location.fast = fast

    ll = list(tz_via_location._iter_tzs())
    zones = [x.zone for x in ll]

    if fast:
        assert zones == [
            'Europe/Rome',
            'Europe/Rome',
            'Europe/Vienna',
            'Europe/Vienna',
            'Europe/Vienna',
        ]
    else:
        assert zones == [
            'Europe/Rome',
            'Europe/Rome',
            'Europe/Ljubljana',
            'Europe/Ljubljana',
            'Europe/Ljubljana',
        ]


def test_past() -> None:
    """
    Should fallback to the 'home' location provider
    """
    dt = fromisoformat('2000-01-01 12:34:45')
    dt = tz_main.localize(dt)
    assert getzone(dt) == 'America/New_York'


def test_future() -> None:
    """
    For locations in the future should rely on 'home' location
    """
    fut = datetime.now() + timedelta(days=100)
    fut = tz_main.localize(fut)
    assert getzone(fut) == 'Europe/Moscow'


def test_get_tz(config) -> None:
    # todo hmm, the way it's implemented at the moment, never returns None?
    get_tz = tz_via_location.get_tz

    # not present in the test data
    tz = get_tz(fromisoformat('2020-01-01 10:00:00'))
    assert notnone(tz).zone == 'Europe/Sofia'

    tz = get_tz(fromisoformat('2017-08-01 11:00:00'))
    assert notnone(tz).zone == 'Europe/Vienna'

    tz = get_tz(fromisoformat('2017-07-30 10:00:00'))
    assert notnone(tz).zone == 'Europe/Rome'

    tz = get_tz(fromisoformat('2020-10-01 14:15:16'))
    assert tz is not None

    on_windows = sys.platform == 'win32'
    if not on_windows:
        tz = get_tz(datetime.min)
        assert tz is not None
    else:
        # seems this fails because windows doesn't support same date ranges
        # https://stackoverflow.com/a/41400321/
        with pytest.raises(OSError):
            get_tz(datetime.min)


def test_policies() -> None:
    naive = fromisoformat('2017-07-30 10:00:00')
    assert naive.tzinfo is None  # just in case

    # actual timezone at the time
    assert getzone(tz_main.localize(naive)) == 'Europe/Rome'

    z = pytz.timezone('America/New_York')
    aware = z.localize(naive)

    assert getzone(tz_main.localize(aware)) == 'America/New_York'

    assert getzone(tz_main.localize(aware, policy='convert')) == 'Europe/Rome'

    with pytest.raises(RuntimeError):
        tz_main.localize(aware, policy='throw')
