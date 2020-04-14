"""
Unified Twitter data (merged from the archive and periodic updates)
"""

from . import twint
from . import archive


def tweets():
    yield from archive.tweets()
    yield from twint.tweets()


# TODO not sure, likes vs favoites??
def likes():
    yield from archive.likes()
    # yield from twint
