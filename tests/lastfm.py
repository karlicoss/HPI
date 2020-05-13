from my.core.cachew import disable_cachew
# TODO need something nicer and integrated inside cachew..
disable_cachew()  # meh

from more_itertools import ilen

from my.lastfm import scrobbles


def test():
    assert ilen(scrobbles()) > 1000


def test_datetime_ascending():
    from more_itertools import pairwise
    for a, b in pairwise(scrobbles()):
        assert a.dt <= b.dt
