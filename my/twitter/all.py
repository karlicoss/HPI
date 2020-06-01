"""
Unified Twitter data (merged from the archive and periodic updates)
"""

# NOTE: you can comment out the sources you don't need
from . import twint, archive

from .common import merge_tweets


def tweets():
    yield from merge_tweets(
        twint  .tweets(),
        archive.tweets(),
    )


def likes():
    yield from merge_tweets(
        twint  .likes(),
        archive.likes(),
    )
