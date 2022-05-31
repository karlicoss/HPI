"""
Twitter data (uses [[https://help.twitter.com/en/managing-your-account/how-to-download-your-twitter-archive][official twitter archive export]])
"""


# before this config was named 'twitter', doesn't make too much sense for archive
# todo unify with other code like this, e.g. time.tz.via_location
try:
    from my.config import twitter_archive as user_config
except ImportError as ie:
    if ie.name != 'twitter_archive':
        raise ie
    try:
        from my.config import twitter as user_config # type: ignore[misc]
    except ImportError:
        raise ie # raise the original exception.. must be something else
    else:
        from ..core import warnings
        warnings.high('my.config.twitter is deprecated! Please rename it to my.config.twitter_archive in your config')
##


from dataclasses import dataclass
import html
from ..core.common import Paths, datetime_aware
from ..core.compat import cached_property
from ..core.error import Res
from ..core.kompress import ZipPath

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



logger = LazyLogger(__name__, level="warning")


def inputs() -> Sequence[Path]:
    return get_files(config.export_path)


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
        res: str = self.raw['full_text']

        ## replace shortened URLS
        repls = [] # from, to, what
        for ue in self.entities['urls']:
            [fr, to] = map(int, ue['indices'])
            repls.append((fr, to, ue['expanded_url']))
        # seems that media field isn't always set
        for me in self.entities.get('media', []):
            [fr, to] = map(int, me['indices'])
            repls.append((fr, to, me['display_url']))
            # todo not sure, maybe use media_url_https instead?
            # for now doing this for compatibility with twint
        repls = list(sorted(repls))
        parts = []
        idx = 0
        for fr, to, what in repls:
            parts.append(res[idx: fr])
            parts.append(what)
            idx = to
        parts.append(res[idx:])
        res = ''.join(parts)
        ##

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
        # todo hmm what is 'extended_entities'
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
        # NOTE: likes basically don't have anything except text and url
        # ugh. I think none means that tweet was deleted?
        res: Optional[str] = self.raw.get('fullText')
        if res is None:
            return None
        res = html.unescape(res)
        return res

    # TODO deprecate?
    @property
    def tid(self) -> TweetId:
        return self.id_str


class ZipExport:
    def __init__(self, archive_path: Path) -> None:
        # todo maybe this should be insude get_files instead, perhps covered with a flag?
        self.zpath = ZipPath(archive_path)

        if (self.zpath / 'tweets.csv').exists():
            from ..core.warnings import high
            high("NOTE: CSV format (pre ~Aug 2018) isn't supported yet, this is likely not going to work.")
        self.old_format = False # changed somewhere around 2020.03
        if not (self.zpath / 'Your archive.html').exists():
            self.old_format = True

    def raw(self, what: str) -> Iterator[Json]:
        logger.info('processing: %s %s', self.zpath, what)

        path = what
        if not self.old_format:
            path = 'data/' + path
        path += '.js'

        ddd = (self.zpath / path).read_text()
        start = ddd.index('[')
        ddd = ddd[start:]
        for j in json.loads(ddd):
            if set(j.keys()) == {what}:
                # newer format
                yield j[what]
            else:
                # older format
                yield j

    @cached_property
    def screen_name(self) -> str:
        [acc] = self.raw('account')
        return acc['username']

    def tweets(self) -> Iterator[Tweet]:
        # NOTE: for some reason, created_at doesn't seem to be in order
        # it mostly is, but there are a bunch of one-off random tweets where the time decreases (typically at the very end)
        for r in self.raw('tweet'):
            yield Tweet(r, screen_name=self.screen_name)


    def likes(self) -> Iterator[Like]:
        # TODO ugh. would be nice to unify Tweet/Like interface
        # however, akeout only got tweetId, full text and url
        for r in self.raw('like'):
            yield Like(r, screen_name=self.screen_name)


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
