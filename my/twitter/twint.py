"""
Twitter data (tweets and favorites). Uses [[https://github.com/twintproject/twint][Twint]] data export.
"""
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import NamedTuple

from my.core import Json, LazyLogger, Paths, Res, Stats, datetime_aware, get_files, stat
from my.core.cfg import make_config
from my.core.sqlite import sqlite_connection

from my.config import twint as user_config  # isort: skip

# TODO move to twitter.twint config structure

@dataclass
class twint(user_config):
    export_path: Paths # path[s]/glob to the twint Sqlite database

####

config = make_config(twint)


log = LazyLogger(__name__)


def get_db_path() -> Path:
    return max(get_files(config.export_path))


from .common import TweetId, permalink


class Tweet(NamedTuple):
    row: Json

    @property
    def id_str(self) -> TweetId:
        return self.row['id_str']

    @property
    def created_at(self) -> datetime_aware:
        seconds = self.row['created_at'] / 1000
        tz = timezone.utc
        # NOTE: UTC seems to be the case at least for the older version of schema I was using
        # in twint, it was extracted from "data-time-ms" field in the scraped HML
        # https://github.com/twintproject/twint/blob/e3345426eb24154ff084be22e4fed5cfa4631930/twint/tweet.py#L85
        #
        # I checked against twitter archive which is definitely UTC, and it seems to match
        # also seems that other people are treating it as utc, e.g.
        # https://github.com/thomasancheriyil/Red-Tide-Detection-based-on-Twitter/blob/beb200be60cc66dcbc394e670513715509837812/python/twitterGapParse.py#L61-L62
        #
        # twint is also saving 'timezone', but this is local machine timezone at the time of scraping?
        # perhaps they thought date-time-ms was local time... or just kept it just in case (they are keeping lots on unnecessary stuff in the db)
        return datetime.fromtimestamp(seconds, tz=tz)

    @property
    def screen_name(self) -> str:
        return self.row['screen_name']

    @property
    def text(self) -> str:
        text = self.row['tweet']
        mentions_s = self.row['mentions']
        if len(mentions_s) > 0:
            # at some point for no apparent reasions mentions stopped appearing from tweet text in twint
            # note that the order is still inconsisnent against twitter archive, but not much we can do
            mentions = mentions_s.split(',')
            for m in mentions:
                # ugh. sometimes they appear as lowercase in text, sometimes not..
                if m.lower() not in text.lower():
                    text = f'@{m} ' + text
        return text

    @property
    def urls(self) -> list[str]:
        ustr = self.row['urls']
        if len(ustr) == 0:
            return []
        return ustr.split(',')

    @property
    def permalink(self) -> str:
        return permalink(screen_name=self.screen_name, id=self.id_str)


    # TODO urls
    def __repr__(self):
        return f'Tweet(id_str={self.id_str}, created_at={self.created_at}, text={self.text})'

# https://github.com/twintproject/twint/issues/196
# ugh. so it dumps everything in tweet table, and there is no good way to tell between fav/original tweet.
# it might result in some tweets missing from the timeline if you happened to like them...
# not sure what to do with it
# alternatively, could ask the user to run separate databases for tweets and favs?
# TODO think about it

_QUERY = '''
SELECT T.*
FROM      tweets    as T
LEFT JOIN favorites as F
ON    T.id_str = F.tweet_id
WHERE {where}
ORDER BY T.created_at
'''


def tweets() -> Iterator[Res[Tweet]]:
    with sqlite_connection(get_db_path(), immutable=True, row_factory='dict') as db:
        res = db.execute(_QUERY.format(where='F.tweet_id IS NULL'))
        yield from map(Tweet, res)


def likes() -> Iterator[Res[Tweet]]:
    with sqlite_connection(get_db_path(), immutable=True, row_factory='dict') as db:
        res = db.execute(_QUERY.format(where='F.tweet_id IS NOT NULL'))
        yield from map(Tweet, res)


def stats() -> Stats:
    return {
        **stat(tweets),
        **stat(likes),
    }
