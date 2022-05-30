"""
Twitter data (uses [[https://help.twitter.com/en/managing-your-account/how-to-download-your-twitter-archive][official twitter archive export]])
"""


# before this config was named 'twitter', doesn't make too much sense for archive
# try to import it defensively..
try:
    from my.config import twitter_archive as user_config
except ImportError as e:
    try:
        from my.config import twitter as user_config
    except ImportError:
        raise e # raise the original exception.. must be something else
    else:
        from ..core import warnings
        warnings.high('my.config.twitter is deprecated! Please rename it to my.config.twitter_archive in your config')


from dataclasses import dataclass
import html
from ..core.common import Paths, datetime_aware
from ..core.error import Res

@dataclass
class twitter_archive(user_config):
    export_path: Paths # path[s]/glob to the twitter archive takeout


###

from ..core.cfg import make_config
config = make_config(twitter_archive)


from datetime import datetime
from typing import List, Optional, NamedTuple, Sequence, Iterator
from pathlib import Path
import json

from ..core.common import get_files, LazyLogger, Json
from ..core import kompress



logger = LazyLogger(__name__, level="warning")


def inputs() -> Sequence[Path]:
    return get_files(config.export_path)[-1:]


from .common import TweetId, permalink


# TODO make sure it's not used anywhere else and simplify interface
class Tweet(NamedTuple):
    raw: Json
    screen_name: str

    @property
    def id_str(self) -> TweetId:
        return self.raw['id_str']

    @property
    def created_at(self) -> datetime_aware:
        dts = self.raw['created_at']
        return datetime.strptime(dts, '%a %b %d %H:%M:%S %z %Y')

    @property
    def permalink(self) -> str:
        return permalink(screen_name=self.screen_name, id=self.id_str)

    @property
    def text(self) -> str:
        res = self.raw['full_text']
        # replace stuff like &lt/&gt
        res = html.unescape(res)
        return res

    @property
    def urls(self) -> List[str]:
        ents = self.entities
        us = ents['urls']
        return [u['expanded_url'] for u in us]

    @property
    def entities(self) -> Json:
        return self.raw['entities']

    def __str__(self) -> str:
        return str(self.raw)

    def __repr__(self) -> str:
        return repr(self.raw)

    # TODO deprecate tid?
    @property
    def tid(self) -> TweetId:
        return self.id_str

    @property
    def dt(self) -> datetime_aware:
        return self.created_at


class Like(NamedTuple):
    raw: Json
    screen_name: str

    @property
    def permalink(self) -> str:
        # doesn'tseem like link it export is more specific...
        return permalink(screen_name=self.screen_name, id=self.id_str)

    @property
    def id_str(self) -> TweetId:
        return self.raw['tweetId']

    @property
    def text(self) -> Optional[str]:
        # ugh. I think none means that tweet was deleted?
        res = self.raw.get('fullText')
        if res is None:
            return None
        res = html.unescape(res)
        return res

    # TODO deprecate?
    @property
    def tid(self) -> TweetId:
        return self.id_str


from functools import lru_cache
class ZipExport:
    def __init__(self, archive_path: Path) -> None:
        # TODO use ZipPath
        self.epath = archive_path

        self.old_format = False # changed somewhere around 2020.03
        if not kompress.kexists(self.epath, 'Your archive.html'):
            self.old_format = True


    def raw(self, what: str): # TODO Json in common?
        logger.info('processing: %s %s', self.epath, what)

        path = what
        if not self.old_format:
            path = 'data/' + path
        path += '.js'

        with kompress.kopen(self.epath, path) as fo:
            ddd = fo.read()
        start = ddd.index('[')
        ddd = ddd[start:]
        for j in json.loads(ddd):
            if set(j.keys()) == {what}:
                # newer format
                yield j[what]
            else:
                # older format
                yield j

    @lru_cache(1)
    def screen_name(self) -> str:
        [acc] = self.raw('account')
        return acc['username']

    def tweets(self) -> Iterator[Tweet]:
        for r in self.raw('tweet'):
            yield Tweet(r, screen_name=self.screen_name())


    def likes(self) -> Iterator[Like]:
        # TODO ugh. would be nice to unify Tweet/Like interface
        # however, akeout only got tweetId, full text and url
        for r in self.raw('like'):
            yield Like(r, screen_name=self.screen_name())


# todo not sure about list and sorting? although can't hurt considering json is not iterative?
def tweets() -> Iterator[Res[Tweet]]:
    for inp in inputs():
        yield from sorted(ZipExport(inp).tweets(), key=lambda t: t.dt)


def likes() -> Iterator[Res[Like]]:
    for inp in inputs():
        yield from ZipExport(inp).likes()


from ..core import stat, Stats
def stats() -> Stats:
    return {
        **stat(tweets),
        **stat(likes),
    }


## Deprecated stuff
Tid = TweetId
