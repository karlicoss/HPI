import sys
from datetime import datetime, time, timedelta

import pytest
import pytz

import my.time.tz.main as tz_main
import my.time.tz.via_location as tz_via_location
from my.core import notnone

from .shared_tz_config import config  # noqa: F401  # autoused fixture


def getzone(dt: datetime) -> str:
    tz = notnone(dt.tzinfo)
    return getattr(tz, 'zone')


@pytest.mark.parametrize('fast', [False, True])
def test_iter_tzs(*, fast: bool, config, monkeypatch: pytest.MonkeyPatch) -> None:
    # TODO hmm.. maybe need to make sure we start with empty config?
    monkeypatch.setattr(config.time.tz.via_location, 'fast', fast)

    ll = list(tz_via_location._iter_tzs())
    zones = [x.zone for x in ll]

    # Check the dates and offsets at local noon in both modes.
    local_noons = [pytz.timezone(x.zone).localize(datetime.combine(x.day, time(12))) for x in ll]
    assert [dt.isoformat() for dt in local_noons] == [
        '2017-07-29T12:00:00+02:00',
        '2017-07-30T12:00:00+02:00',
        '2017-07-31T12:00:00+02:00',
        '2017-08-01T12:00:00+02:00',
        '2017-08-02T12:00:00+02:00',
    ]

    if fast:
        # The approximate finder can choose a neighboring zone near borders.
        assert zones == [
            'Europe/Rome',
            'Europe/Rome',
            'Europe/Rome',
            'Europe/Rome',
            'Europe/Ljubljana',
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
    dt = datetime.fromisoformat('2000-01-01 12:34:45')
    dt = tz_main.localize(dt)
    assert getzone(dt) == 'America/New_York'


def test_future() -> None:
    """
    For locations in the future should rely on 'home' location
    """
    fut = datetime.now() + timedelta(days=100)
    fut = tz_main.localize(fut)
    assert getzone(fut) == 'Europe/Moscow'


@pytest.mark.parametrize('fast', [False, True])
def test_get_tz(*, fast: bool, config, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config.time.tz.via_location, 'fast', fast)
    # Rebuild the cached mapping after changing the finder mode.
    tz_via_location._day2zone.cache_clear()

    # todo hmm, the way it's implemented at the moment, never returns None?
    get_tz = tz_via_location.get_tz

    # not present in the test data
    dt = datetime.fromisoformat('2020-01-01 10:00:00')
    tz = notnone(get_tz(dt))
    assert tz.localize(dt).isoformat() == '2020-01-01T10:00:00+02:00'
    assert tz.zone == 'Europe/Sofia'

    dt = datetime.fromisoformat('2017-08-01 11:00:00')
    tz = notnone(get_tz(dt))
    assert tz.localize(dt).isoformat() == '2017-08-01T11:00:00+02:00'
    if fast:
        assert tz.zone == 'Europe/Rome'
    else:
        assert tz.zone == 'Europe/Ljubljana'

    dt = datetime.fromisoformat('2017-07-30 10:00:00')
    tz = notnone(get_tz(dt))
    assert tz.localize(dt).isoformat() == '2017-07-30T10:00:00+02:00'
    assert tz.zone == 'Europe/Rome'

    dt = datetime.fromisoformat('2020-10-01 14:15:16')
    tz = notnone(get_tz(dt))
    assert tz.localize(dt).isoformat() == '2020-10-01T14:15:16+03:00'
    assert tz.zone == 'Europe/Moscow'

    on_windows = sys.platform == 'win32'
    if not on_windows:
        assert get_tz(datetime.min) is not None
    else:
        # seems this fails because windows doesn't support same date ranges
        # https://stackoverflow.com/a/41400321/
        with pytest.raises(OSError):
            get_tz(datetime.min)


def test_policies() -> None:
    naive = datetime.fromisoformat('2017-07-30 10:00:00')
    assert naive.tzinfo is None  # just in case

    # actual timezone at the time
    assert getzone(tz_main.localize(naive)) == 'Europe/Rome'

    z = pytz.timezone('America/New_York')
    aware = z.localize(naive)

    assert getzone(tz_main.localize(aware)) == 'America/New_York'

    assert getzone(tz_main.localize(aware, policy='convert')) == 'Europe/Rome'

    with pytest.raises(RuntimeError):
        tz_main.localize(aware, policy='throw')
