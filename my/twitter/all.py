"""
Unified Twitter data (merged from the archive and periodic updates)
"""
from itertools import chain

from . import twint
from . import archive


from more_itertools import unique_everseen


def merge_tweets(*sources):
    yield from unique_everseen(
        chain(*sources),
        key=lambda t: t.id_str,
    )


def tweets():
    # NOTE order matters.. twint seems to contain better data
    # todo probably, worthy an investigation..
    yield from merge_tweets(twint.tweets(), archive.tweets())


# TODO not sure, likes vs favoites??
def likes():
    yield from merge_tweets(archive.likes())
    # yield from twint
