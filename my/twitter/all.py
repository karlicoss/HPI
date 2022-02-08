"""
Unified Twitter data (merged from the archive and periodic updates)
"""
from typing import Iterator
from ..core import Res
from ..core.source import import_source
from .common import merge_tweets, Tweet


# NOTE: you can comment out the sources you don't need
src_twint   = import_source(module_name=f'my.twitter.twint')
src_archive = import_source(module_name=f'my.twitter.archive')


@src_twint
def _tweets_twint() -> Iterator[Res[Tweet]]:
    from . import twint as src
    return src.tweets()

@src_archive
def _tweets_archive() -> Iterator[Res[Tweet]]:
    from . import archive as src
    return src.tweets()


@src_twint
def _likes_twint() -> Iterator[Res[Tweet]]:
    from . import twint as src
    return src.likes()

@src_archive
def _likes_archive() -> Iterator[Res[Tweet]]:
    from . import archive as src
    return src.likes()


def tweets() -> Iterator[Res[Tweet]]:
    yield from merge_tweets(
        _tweets_twint(),
        _tweets_archive(),
    )


def likes() -> Iterator[Res[Tweet]]:
    yield from merge_tweets(
        _likes_twint(),
        _likes_archive(),
    )


# TODO maybe to avoid all the boilerplate above could use some sort of module Protocol?
