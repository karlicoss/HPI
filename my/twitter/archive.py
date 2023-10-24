"""
Twitter data (uses [[https://help.twitter.com/en/managing-your-account/how-to-download-your-twitter-archive][official twitter archive export]])
"""


# before this config was named 'twitter', doesn't make too much sense for archive
# todo unify with other code like this, e.g. time.tz.via_location
try:
    from my.config import twitter_archive as user_config
except ImportError as ie:
    if not (ie.name == 'my.config' and 'twitter_archive' in str(ie)):
        # must be caused by something else
        raise ie
    try:
        from my.config import twitter as user_config # type: ignore[assignment]
    except ImportError:
        raise ie # raise the original exception.. must be something else
    else:
        from ..core import warnings
        warnings.high('my.config.twitter is deprecated! Please rename it to my.config.twitter_archive in your config')
##


from dataclasses import dataclass
from datetime import datetime
from itertools import chain
import json  # hmm interesting enough, orjson didn't give much speedup here?
from pathlib import Path
from functools import cached_property
import html
from typing import (
    Iterator,
    List,
    Optional,
    Sequence,
)

from more_itertools import unique_everseen

from my.core import (
    datetime_aware,
    get_files,
    make_logger,
    stat,
    Json,
    Paths,
    Res,
    Stats,
)
from my.core import warnings
from my.core.cfg import make_config
from my.core.serialize import dumps as json_dumps

from .common import TweetId, permalink


@dataclass
class twitter_archive(user_config):
    export_path: Paths  # path[s]/glob to the twitter archive takeout


###

config = make_config(twitter_archive)


logger = make_logger(__name__)


def inputs() -> Sequence[Path]:
    return get_files(config.export_path)


# TODO make sure it's not used anywhere else and simplify interface
@dataclass
class Tweet:
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
        repls = []  # from, to, what
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
            parts.append(res[idx:fr])
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


@dataclass
class Like:
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
        self.zpath = archive_path
        if (self.zpath / 'tweets.csv').exists():
            warnings.high("NOTE: CSV format (pre ~Aug 2018) isn't supported yet, this is likely not going to work.")
        self.old_format = False  # changed somewhere around 2020.03
        if not (self.zpath / 'Your archive.html').exists():
            self.old_format = True

    def raw(self, what: str, *, fname: Optional[str] = None) -> Iterator[Json]:
        logger.info(f'{self.zpath} : processing {what}')

        path = fname or what
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
        [acc] = self.raw(what='account')
        return acc['username']

    def tweets(self) -> Iterator[Tweet]:
        fname = 'tweets'  # since somewhere between mar and oct 2022
        if not (self.zpath / f'data/{fname}.js').exists():
            fname = 'tweet'  # old name
        # NOTE: for some reason, created_at doesn't seem to be in order
        # it mostly is, but there are a bunch of one-off random tweets where the time decreases (typically at the very end)
        for r in self.raw(what='tweet', fname=fname):
            yield Tweet(r, screen_name=self.screen_name)

    def likes(self) -> Iterator[Like]:
        # TODO ugh. would be nice to unify Tweet/Like interface
        # however, akeout only got tweetId, full text and url
        for r in self.raw(what='like'):
            yield Like(r, screen_name=self.screen_name)


# todo not sure about list and sorting? although can't hurt considering json is not iterative?
def tweets() -> Iterator[Res[Tweet]]:
    _all = chain.from_iterable(ZipExport(i).tweets() for i in inputs())
    res = unique_everseen(_all, key=json_dumps)
    yield from sorted(res, key=lambda t: t.dt)


def likes() -> Iterator[Res[Like]]:
    _all = chain.from_iterable(ZipExport(i).likes() for i in inputs())
    res = unique_everseen(_all, key=json_dumps)
    # ugh. likes don't have datetimes..
    yield from res


def stats() -> Stats:
    return {
        **stat(tweets),
        **stat(likes),
    }


## Deprecated stuff
Tid = TweetId
