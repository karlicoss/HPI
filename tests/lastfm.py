from more_itertools import ilen

from my.lastfm import scrobbles


def test():
    assert ilen(scrobbles()) > 1000
