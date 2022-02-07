"""
Twitter data from Talon app database (in =/data/data/com.klinker.android.twitter_l/databases/=)
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterator, Sequence, Optional, Dict


from my.config import twitter as user_config


from ..core import Paths
@dataclass
class config(user_config.talon):
    # paths[s]/glob to the exported sqlite databases
    export_path: Paths


from ..core import get_files
from pathlib import Path
def inputs() -> Sequence[Path]:
    return get_files(config.export_path)



@dataclass(unsafe_hash=True)
class Tweet:
    id_str: str
    # TODO figure out if utc
    created_at: datetime
    screen_name: str
    text: str
    urls: Sequence[str]


# meh... just wrappers to tell apart tweets from favorites...
@dataclass(unsafe_hash=True)
class _IsTweet:
    tweet: Tweet
@dataclass(unsafe_hash=True)
class _IsFavorire:
    tweet: Tweet


from typing import Union
from ..core.error import Res
from ..core.dataset import connect_readonly
Entity = Union[_IsTweet, _IsFavorire]
def _entities() -> Iterator[Res[Entity]]:
    for f in inputs():
        yield from _process_one(f)


def _process_one(f: Path) -> Iterator[Res[Entity]]:
    handlers = {
        'user_tweets.db'    : _process_user_tweets,
        'favorite_tweets.db': _process_favorite_tweets,
    }
    fname = f.name
    handler = handlers.get(fname)
    if handler is None:
        yield RuntimeError(f"Coulnd't find handler for {fname}")
        return
    with connect_readonly(f) as db:
        yield from handler(db)


def _process_user_tweets(db) -> Iterator[Res[Entity]]:
    # dunno why it's called 'lists'
    for r in db['lists'].all(order_by='time'):
        try:
            yield _IsTweet(_parse_tweet(r))
        except Exception as e:
            yield e


def _process_favorite_tweets(db) -> Iterator[Res[Entity]]:
    for r in db['favorite_tweets'].all(order_by='time'):
        try:
            yield _IsFavorire(_parse_tweet(r))
        except Exception as e:
            yield e

def _parse_tweet(row) -> Tweet:
    # TODO row['retweeter] if not empty, would be user's name and means retweet?
    # screen name would be the actual tweet's author
    return Tweet(
        id_str=str(row['tweet_id']),
        created_at=datetime.fromtimestamp(row['time'] / 1000),
        screen_name=row['screen_name'],
        text=row['text'],
        # todo hmm text sometimes is trimmed with ellipsis? at least urls
        urls=tuple(u for u in row['other_url'].split(' ') if len(u.strip()) > 0),
    )


from more_itertools import unique_everseen
def tweets() -> Iterator[Res[Tweet]]:
    for x in unique_everseen(_entities()):
        if isinstance(x, Exception):
            yield x
        elif isinstance(x, _IsTweet):
            yield x.tweet

def likes() -> Iterator[Res[Tweet]]:
    for x in unique_everseen(_entities()):
        if isinstance(x, Exception):
            yield x
        elif isinstance(x, _IsFavorire):
            yield x.tweet

