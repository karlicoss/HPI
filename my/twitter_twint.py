"""
Twitter data (tweets and favorites). Uses [[https://github.com/twintproject/twint][Twint]] data export.
"""

from datetime import datetime
from typing import NamedTuple, Iterable
from pathlib import Path

from .common import PathIsh, get_files, LazyLogger, Json
from .core.time import abbr_to_timezone

from my.config import twint as config


log = LazyLogger(__name__)


def get_db_path() -> Path:
    # TODO don't like the hardcoded extension. maybe, config should decide?
    # or, glob only applies to directories?
    return max(get_files(config.export_path, glob='*.db'))


class Tweet(NamedTuple):
    row: Json

    @property
    def id_str(self) -> str:
        return self.row['id_str']

    @property
    def created_at(self) -> datetime:
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
    def permalink(self) -> str:
        return f'https://twitter.com/{self.screen_name}/status/{self.id_str}'


    # TODO urls
    def __repr__(self):
        return f'Tweet(id_str={self.id_str}, created_at={self.created_at}, text={self.text})'


def tweets() -> Iterable[Tweet]:
    import dataset # type: ignore
    db_path = get_db_path()
    # TODO check that exists?
    db = dataset.connect(f'sqlite:///{db_path}')
    tdb = db.load_table('tweets')
    yield from map(Tweet, tdb.all(order_by='created_at'))
