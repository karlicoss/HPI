from pathlib import Path

import pytest
import pytz

from my.body.weight import from_orgmode
from my.core.cfg import tmp_config


def test_body_weight() -> None:
    weights = [0.0 if isinstance(x, Exception) else x.value for x in from_orgmode()]

    assert weights == [
        0.0,
        62.0,
        0.0,
        61.0,
        62.0,
        0.0,
    ]


@pytest.fixture(autouse=True)
def prepare(tmp_path: Path):
    ndir = tmp_path / 'notes'
    ndir.mkdir()
    logs = ndir / 'logs.org'
    logs.write_text(
        '''
#+TITLE: Stuff I'm logging

* Weight (org-capture) :weight:
** [2020-05-01 Fri 09:00] 62
** 63
    this should be ignored, got no timestamp
** [2020-05-03 Sun 08:00] 61
** [2020-05-04 Mon 10:00] 62
'''
    )
    misc = ndir / 'misc.org'
    misc.write_text(
        '''
Some misc stuff

* unrelated note :weight:whatever:
'''
    )

    class orgmode:
        paths = [ndir]

    class weight:
        # TODO ugh. this belongs to tz provider or global config or something
        default_timezone = pytz.timezone('Europe/London')

    with tmp_config() as cfg:
        cfg.orgmode = orgmode
        cfg.weight = weight
        yield
