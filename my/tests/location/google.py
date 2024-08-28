"""
Tests for LEGACY location provider

Keeping for now for backwards compatibility
"""

from pathlib import Path

import pytest
from more_itertools import one

from my.core.cfg import tmp_config
from my.location.google import locations


def test_google_locations() -> None:
    locs = list(locations())
    assert len(locs) == 3810, len(locs)

    last = locs[-1]
    assert last.dt.strftime('%Y%m%d %H:%M:%S') == '20170802 13:01:56'  # should be utc
    # todo approx
    assert last.lat == 46.5515350
    assert last.lon == 16.4742742
    # todo check altitude


@pytest.fixture(autouse=True)
def prepare(tmp_path: Path):

    # TODO could just pick a part of shared config? not sure
    _takeout_path = _prepare_takeouts_dir(tmp_path)

    class google:
        takeout_path = _takeout_path

    with tmp_config() as config:
        config.google = google
        yield


def _prepare_takeouts_dir(tmp_path: Path) -> Path:
    from ..common import testdata

    try:
        track = one(testdata().rglob('italy-slovenia-2017-07-29.json'))
    except ValueError as e:
        raise RuntimeError('testdata not found, setup git submodules?') from e

    # todo ugh. unnecessary zipping, but at the moment takeout provider doesn't support plain dirs
    import zipfile

    with zipfile.ZipFile(tmp_path / 'takeout.zip', 'w') as zf:
        zf.writestr('Takeout/Location History/Location History.json', track.read_bytes())
    return tmp_path
