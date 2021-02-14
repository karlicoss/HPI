from .common import skip_if_not_karlicoss as pytestmark

# todo maybe belongs to common
from more_itertools import ilen


def test() -> None:
    from my.lastfm import scrobbles
    assert ilen(scrobbles()) > 1000


def test_datetime_ascending() -> None:
    from my.lastfm import scrobbles
    from more_itertools import pairwise
    for a, b in pairwise(scrobbles()):
        assert a.dt <= b.dt
