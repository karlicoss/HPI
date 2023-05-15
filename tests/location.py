from pathlib import Path

import pytest


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
    from .shared_config import temp_config
    user_config = temp_config(tmp_path)

    import my.core.cfg as C
    with C.tmp_config() as config:
        config.google = user_config.google
        yield

