"""
Helper to test various timezone/location dependent things
"""

from datetime import date, datetime, timezone
from pathlib import Path

import pytest
from more_itertools import one

from my.core.cfg import tmp_config


@pytest.fixture(autouse=True)
def config(tmp_path: Path):
    # TODO could just pick a part of shared config? not sure
    _takeout_path = _prepare_takeouts_dir(tmp_path)

    class google:
        takeout_path = _takeout_path

    class location:
        # fmt: off
        home = (
            # supports ISO strings
            ('2005-12-04'                                       , (42.697842, 23.325973)), # Bulgaria, Sofia
            # supports date/datetime objects
            (date(year=1980, month=2, day=15)                   , (40.7128  , -74.0060 )), # NY
            # check tz handling..
            (datetime.fromtimestamp(1600000000, tz=timezone.utc), (55.7558  , 37.6173  )), # Moscow, Russia
        )
        # fmt: on
        # note: order doesn't matter, will be sorted in the data provider

    class time:
        class tz:
            class via_location:
                fast = True  # some tests rely on it

    with tmp_config() as cfg:
        cfg.google = google
        cfg.location = location
        cfg.time = time
        yield cfg


def _prepare_takeouts_dir(tmp_path: Path) -> Path:
    from .common import testdata

    testdata_dir = testdata()
    try:
        track = one(testdata_dir.rglob('italy-slovenia-2017-07-29.json'))
    except ValueError as e:
        raise RuntimeError(f'testdata not found in {testdata_dir}, setup git submodules?') from e

    # todo ugh. unnecessary zipping, but at the moment takeout provider doesn't support plain dirs
    import zipfile

    with zipfile.ZipFile(tmp_path / 'takeout.zip', 'w') as zf:
        zf.writestr('Takeout/Location History/Location History.json', track.read_bytes())
    return tmp_path
