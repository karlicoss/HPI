"""
Twitter data from Talon app database (in =/data/data/com.klinker.android.twitter_l/databases/=)
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re
from typing import Iterator, Sequence, Optional, Dict

import pytz

from my.config import twitter as user_config


from ..core import Paths, Res, datetime_aware
@dataclass
class config(user_config.talon):
    # paths[s]/glob to the exported sqlite databases
    export_path: Paths


from ..core import get_files
from pathlib import Path
def inputs() -> Sequence[Path]:
    return get_files(config.export_path)


from .common import TweetId, permalink


@dataclass(unsafe_hash=True)
class Tweet:
    id_str: TweetId
    created_at: datetime_aware
    screen_name: str
    text: str
    urls: Sequence[str]

    @property
    def permalink(self) -> str:
        return permalink(screen_name=self.screen_name, id=self.id_str)


# meh... just wrappers to tell apart tweets from favorites...
@dataclass(unsafe_hash=True)
class _IsTweet:
    tweet: Tweet
@dataclass(unsafe_hash=True)
class _IsFavorire:
    tweet: Tweet


from typing import Union
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
    # ok so looks like it's tz aware..
    # https://github.com/klinker24/talon-for-twitter-android/blob/c3b0612717ba3ea93c0cae6d907d7d86d640069e/app/src/main/java/com/klinker/android/twitter_l/data/sq_lite/FavoriteTweetsDataSource.java#L95
    # uses https://docs.oracle.com/javase/7/docs/api/java/util/Date.html#getTime()
    # and it's created here, so looks like it's properly parsed from the api
    # https://github.com/Twitter4J/Twitter4J/blob/8376fade8d557896bb9319fb46e39a55b134b166/twitter4j-core/src/internal-json/java/twitter4j/ParseUtil.java#L69-L79
    created_at = datetime.fromtimestamp(row['time'] / 1000, tz=pytz.utc)
    text = row['text']

    # try explanding URLs.. sadly there are no positions in the db
    urls = row['other_url'].split()
    if len(urls) > 0:
        ellipsis = '...'
        # might have something collapsed
        # e.g. deepmind.com/blog/article/Comp...
        # NOTE: need a one character of lookahead to split on ellipsis.. hence ?=
        for short in re.findall(r'(?:^|\s)([\S]+)' + re.escape(ellipsis) + r'(?=\s|$)', text):
            for full in urls:
                if short in full:
                    text = text.replace(short + ellipsis, full)
                    break
    #

    screen_name = row['screen_name']
    # considering id_str is referring to the retweeter's tweet (rather than the original tweet)
    # makes sense for the permalink to contain the retweeter as well
    # also makes it more compatible to twitter archive
    # a bit sad to lose structured information about RT, but then again we could always just parse it..
    retweeter = row['retweeter']
    if len(retweeter) > 0:
        text = f'RT @{screen_name}: {text}'
        screen_name = retweeter

    return Tweet(
        id_str=str(row['tweet_id']),
        created_at=created_at,
        screen_name=screen_name,
        text=text,
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


# TODO maybe should combine all public iterators into a stats()
