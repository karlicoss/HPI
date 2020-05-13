"""
Unified Twitter data (merged from the archive and periodic updates)
"""
from itertools import chain

from . import twint
from . import archive


# TODO move to .common?
def merge_tweets(*sources):
    from more_itertools import unique_everseen
    yield from unique_everseen(
        chain(*sources),
        key=lambda t: t.id_str,
    )


def tweets():
    yield from merge_tweets(twint.tweets(), archive.tweets())


def likes():
    yield from merge_tweets(twint.likes(), archive.likes())
