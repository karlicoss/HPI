from pathlib import Path

from more_itertools import one

import pytest # type: ignore


def test() -> None:
    from my.location.google import locations
    locs = list(locations())
    assert len(locs) == 3810

    last = locs[-1]
    assert last.dt.strftime('%Y%m%d %H:%M:%S') == '20170802 13:01:56' # should be utc
    # todo approx
    assert last.lat == 46.5515350
    assert last.lon == 16.4742742
    # todo check altitude


@pytest.fixture(autouse=True)
def prepare(tmp_path: Path):
    from .common import reset_modules
    reset_modules()

    user_config = _prepare_google_config(tmp_path)

    import my.core.cfg as C
    with C.tmp_config() as config:
        config.google = user_config # type: ignore
        yield


def _prepare_google_config(tmp_path: Path):
    from .common import testdata
    track = one(testdata().rglob('italy-slovenia-2017-07-29.json'))

    # todo ugh. unnecessary zipping, but at the moment takeout provider doesn't support plain dirs
    import zipfile
    with zipfile.ZipFile(tmp_path / 'takeout.zip', 'w') as zf:
        zf.writestr('Takeout/Location History/Location History.json', track.read_bytes())

    class google_config:
        takeout_path = tmp_path
    return google_config
