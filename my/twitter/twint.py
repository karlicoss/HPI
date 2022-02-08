"""
Twitter data (tweets and favorites). Uses [[https://github.com/twintproject/twint][Twint]] data export.
"""

REQUIRES = ['dataset']

from ..core.common import Paths
from ..core.error import Res
from dataclasses import dataclass
from my.config import twint as user_config

# TODO move to twitter.twint config structure

@dataclass
class twint(user_config):
    export_path: Paths # path[s]/glob to the twint Sqlite database

####

from ..core.cfg import make_config
config = make_config(twint)


from datetime import datetime
from typing import NamedTuple, Iterator, List
from pathlib import Path

from ..core.common import get_files, LazyLogger, Json, datetime_aware
from ..core.time import abbr_to_timezone

log = LazyLogger(__name__)


def get_db_path() -> Path:
    return max(get_files(config.export_path))


class Tweet(NamedTuple):
    row: Json

    @property
    def id_str(self) -> str:
        return self.row['id_str']

    @property
    def created_at(self) -> datetime_aware:
        seconds = self.row['created_at'] / 1000
        tz_abbr = self.row['timezone']
        tz = abbr_to_timezone(tz_abbr)
        dt = datetime.fromtimestamp(seconds, tz=tz)
        return dt

    # TODO permalink -- take user into account?
    @property
    def screen_name(self) -> str:
        return self.row['screen_name']

    @property
    def text(self) -> str:
        return self.row['tweet']

    @property
    def urls(self) -> List[str]:
        ustr = self.row['urls']
        if len(ustr) == 0:
            return []
        return ustr.split(',')

    # TODO move to common
    @property
    def permalink(self) -> str:
        return f'https://twitter.com/{self.screen_name}/status/{self.id_str}'


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

def _get_db():
    from ..core.dataset import connect_readonly
    db_path = get_db_path()
    return connect_readonly(db_path)


def tweets() -> Iterator[Res[Tweet]]:
    db = _get_db()
    res = db.query(_QUERY.format(where='F.tweet_id IS NULL'))
    yield from map(Tweet, res)


def likes() -> Iterator[Res[Tweet]]:
    db = _get_db()
    res = db.query(_QUERY.format(where='F.tweet_id IS NOT NULL'))
    yield from map(Tweet, res)


from ..core import stat, Stats
def stats() -> Stats:
    return {
        **stat(tweets),
        **stat(likes),
    }
