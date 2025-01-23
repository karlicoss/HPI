"""
Twitter data (uses [[https://help.twitter.com/en/managing-your-account/how-to-download-your-twitter-archive][official twitter archive export]])
"""

from __future__ import annotations

import html
import json  # hmm interesting enough, orjson didn't give much speedup here?
from abc import abstractmethod
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from datetime import datetime
from functools import cached_property
from itertools import chain
from pathlib import Path
from typing import (
    TYPE_CHECKING,
)

from more_itertools import unique_everseen

from my.core import (
    Json,
    Paths,
    Res,
    Stats,
    datetime_aware,
    get_files,
    make_logger,
    stat,
    warnings,
)
from my.core.serialize import dumps as json_dumps

from .common import TweetId, permalink

logger = make_logger(__name__)


class config:
    @property
    @abstractmethod
    def export_path(self) -> Paths:
        """path[s]/glob to the twitter archive takeout"""
        raise NotImplementedError


def make_config() -> config:
    # before this config was named 'twitter', doesn't make too much sense for archive
    # todo unify with other code like this, e.g. time.tz.via_location
    try:
        from my.config import twitter_archive as user_config
    except ImportError as ie:
        if not (ie.name == 'my.config' and 'twitter_archive' in str(ie)):
            # must be caused by something else
            raise ie
        try:
            from my.config import twitter as user_config  # type: ignore[assignment]
        except ImportError:
            raise ie  # raise the original exception.. must be something else  # noqa: B904
        else:
            warnings.high('my.config.twitter is deprecated! Please rename it to my.config.twitter_archive in your config')
    ##

    class combined_config(user_config, config):
        pass

    return combined_config()


def inputs() -> Sequence[Path]:
    return get_files(make_config().export_path)


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
        repls = sorted(repls)
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
    def urls(self) -> list[str]:
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
    def text(self) -> str | None:
        # NOTE: likes basically don't have anything except text and url
        # ugh. I think none means that tweet was deleted?
        res: str | None = self.raw.get('fullText')
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

    def raw(self, what: str, *, fname: str | None = None) -> Iterator[Json]:
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


def _cleanup_tweet_json(rj: Json) -> None:
    # note: for now this isn't used, was just an attempt to normalise raw data...

    rj.pop('edit_info', None)  # useless for downstream processing, but results in dupes, so let's remove it

    ## could probably just take the last one? dunno
    rj.pop('retweet_count', None)
    rj.pop('favorite_count', None)
    ##

    entities = rj.get('entities', {})
    ext_entities = rj.get('extended_entities', {})

    # TODO shit. unclear how to 'merge' changes to these
    # links sometimes change for no apparent reason -- and sometimes old one is still valid but not the new one???
    for m in entities.get('media', {}):
        m.pop('media_url', None)
        m.pop('media_url_https', None)
    for m in ext_entities.get('media', {}):
        m.pop('media_url', None)
        m.pop('media_url_https', None)
    ##

    for m in entities.get('user_mentions', {}):
        # changes if user renames themselves...
        m.pop('name', None)

    # hmm so can change to -1? maybe if user was deleted?
    # but also can change to actually something else?? second example
    entities.pop('user_mentions', None)

    # TODO figure out what else is changing there later...
    rj.pop('entities', None)
    rj.pop('extended_entities', None)

    ## useless attributes which should be fine to exclude
    rj.pop('possibly_sensitive', None)  # not sure what is this.. sometimes appears with False value??
    rj.pop('withheld_in_countries', None)
    rj.pop('lang', None)
    ##

    # ugh. might change if the Twitter client was deleted or description renamed??
    rj.pop('source', None)

    ## ugh. sometimes trailing 0 after decimal point is present?
    rj.pop('coordinates', None)
    rj.get('geo', {}).pop('coordinates', None)
    ##

    # ugh. this changes if user changed their name...
    # or disappears if account was deleted?
    rj.pop('in_reply_to_screen_name', None)


# todo not sure about list and sorting? although can't hurt considering json is not iterative?
def tweets() -> Iterator[Res[Tweet]]:
    _all = chain.from_iterable(ZipExport(i).tweets() for i in inputs())

    # NOTE raw json data in archived tweets changes all the time even for same tweets
    # there is an attempt to clean it up... but it's tricky since users rename themselves, twitter stats are changing
    # so it's unclear how to pick up
    # we should probably 'merge' tweets into a canonical version, e.g.
    # - pick latest tweet stats
    # - keep history of usernames we were replying to that share the same user id
    # - pick 'best' media url somehow??
    # - normalise coordinates data
    def key(t: Tweet):
        # NOTE: not using t.text, since it actually changes if entities in tweet are changing...
        # whereas full_text seems stable
        text = t.raw['full_text']
        return (t.created_at, t.id_str, text)

    res = unique_everseen(_all, key=key)
    yield from sorted(res, key=lambda t: t.created_at)


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
if not TYPE_CHECKING:
    Tid = TweetId
