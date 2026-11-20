"""
Helper to test various timezone/location dependent things
"""

from datetime import UTC, date, datetime
from pathlib import Path
from zipfile import ZipFile

import pytest

from my.core.cfg import tmp_config

from .common import testdata


@pytest.fixture(autouse=True)
def config():
    class location:
        home = (
            # supports ISO strings
            ('2005-12-04'                              , (42.697842, 23.325973)), # Bulgaria, Sofia
            # supports date/datetime objects
            (date(year=1980, month=2, day=15)          , (40.7128  , -74.0060 )), # NY
            # check tz handling..
            (datetime.fromtimestamp(1600000000, tz=UTC), (55.7558  , 37.6173  )), # Moscow, Russia
        )  # fmt: skip
        # note: order doesn't matter, will be sorted in the data provider

    class time:
        class tz:
            class via_location:
                fast = True  # some tests rely on it

    with tmp_config() as cfg:
        cfg.location = location
        cfg.time = time
        yield cfg


@pytest.fixture(autouse=True)
def takeout_archive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from my.google.takeout import parser

    archive = tmp_path / 'takeout.zip'
    track = testdata() / 'track' / 'testdata' / 'italy-slovenia-2017-07-29.json'
    with ZipFile(archive, 'w') as zf:
        zf.write(track, 'Takeout/Location History/Location History.json')
    monkeypatch.setattr(parser.config, 'takeout_path', archive)
