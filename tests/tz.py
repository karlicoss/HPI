from datetime import datetime, timedelta
from pathlib import Path
import sys

import pytest # type: ignore

import my.time.tz.main as TZ
import my.time.tz.via_location as LTZ


def test_iter_tzs() -> None:
    ll = list(LTZ._iter_tzs())
    assert len(ll) > 3


def test_future() -> None:
    fut = datetime.now() + timedelta(days=100)
    # shouldn't crash at least
    assert TZ.localize(fut) is not None


def test_tz() -> None:
    # not present in the test data
    tz = LTZ._get_tz(D('20200101 10:00:00'))
    assert tz is None

    tz = LTZ._get_tz(D('20170801 11:00:00'))
    assert tz is not None
    assert tz.zone == 'Europe/Vienna'

    tz = LTZ._get_tz(D('20170730 10:00:00'))
    assert tz is not None
    assert tz.zone == 'Europe/Rome'


def D(dstr: str) -> datetime:
    return datetime.strptime(dstr, '%Y%m%d %H:%M:%S')


# TODO copy pasted from location.py, need to extract some common provider
@pytest.fixture(autouse=True)
def prepare(tmp_path: Path):
    LTZ._FASTER = True

    from more_itertools import one
    testdata = Path(__file__).absolute().parent.parent / 'testdata'
    assert testdata.exists(), testdata

    track = one(testdata.rglob('italy-slovenia-2017-07-29.json'))

    # todo ugh. unnecessary zipping, but at the moment takeout provider doesn't support plain dirs
    import zipfile
    with zipfile.ZipFile(tmp_path / 'takeout.zip', 'w') as zf:
        zf.writestr('Takeout/Location History/Location History.json', track.read_bytes())

    # FIXME ugh. early import/inheritance of user_confg in my.google.takeout.paths messes things up..
    from my.cfg import config
    class user_config:
        takeout_path = tmp_path
    config.google = user_config # type: ignore

    yield
