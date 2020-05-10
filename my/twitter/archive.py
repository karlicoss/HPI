"""
Twitter data (uses [[https://help.twitter.com/en/managing-your-account/how-to-download-your-twitter-archive][official twitter archive export]])
"""
from dataclasses import dataclass
from ..core.common import Paths

from my.config import twitter as user_config

@dataclass
class twitter(user_config):
    export_path: Paths # path[s]/glob to the twitter archive takeout


###

from ..core.cfg import make_config
config = make_config(twitter)


from datetime import datetime
from typing import Union, List, Dict, Set, Optional, Iterator, Any, NamedTuple
from pathlib import Path
from functools import lru_cache
import json
import zipfile

import pytz

from ..common import PathIsh, get_files, LazyLogger, Json
from ..kython import kompress



logger = LazyLogger(__name__)


def _get_export() -> Path:
    return max(get_files(config.export_path))


Tid = str


# TODO make sure it's not used anywhere else and simplify interface
class Tweet(NamedTuple):
    raw: Json
    screen_name: str

    @property
    def id_str(self) -> str:
        return self.raw['id_str']

    @property
    def created_at(self) -> datetime:
        dts = self.raw['created_at']
        return datetime.strptime(dts, '%a %b %d %H:%M:%S %z %Y')

    @property
    def permalink(self) -> str:
        return f'https://twitter.com/{self.screen_name}/status/{self.tid}'

    @property
    def text(self) -> str:
        return self.raw['full_text']

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
    def tid(self) -> Tid:
        return self.id_str

    @property
    def dt(self) -> datetime:
        return self.created_at


class Like(NamedTuple):
    raw: Json
    screen_name: str

    # TODO need to make permalink/link/url consistent across my stuff..
    @property
    def permalink(self) -> str:
        # doesn'tseem like link it export is more specific...
        return f'https://twitter.com/{self.screen_name}/status/{self.tid}'

    @property
    def id_str(self) -> Tid:
        return self.raw['tweetId']

    @property
    def text(self) -> Optional[str]:
        # ugh. I think none means that tweet was deleted?
        return self.raw.get('fullText')

    # TODO deprecate?
    @property
    def tid(self) -> Tid:
        return self.id_str


class ZipExport:
    def __init__(self) -> None:
        self.epath = _get_export()

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


def tweets() -> List[Tweet]:
    return list(sorted(ZipExport().tweets(), key=lambda t: t.dt))


def likes() -> List[Like]:
    return list(ZipExport().likes())


def test_tweet():
    raw = """
 {
  "retweeted" : false,
  "entities" : {
    "hashtags" : [ ],
    "symbols" : [ ],
    "user_mentions" : [ ],
    "urls" : [ {
      "url" : "https://t.co/vUg4W6nxwU",
      "expanded_url" : "https://intelligence.org/2013/12/13/aaronson/",
      "display_url" : "intelligence.org/2013/12/13/aar…",
      "indices" : [ "120", "143" ]
    }
    ]
  },
  "display_text_range" : [ "0", "90" ],
  "favorite_count" : "0",
  "in_reply_to_status_id_str" : "24123424",
  "id_str" : "2328934829084",
  "in_reply_to_user_id" : "23423424",
  "truncated" : false,
  "retweet_count" : "0",
  "id" : "23492349032940",
  "in_reply_to_status_id" : "23482984932084",
  "created_at" : "Thu Aug 30 07:12:48 +0000 2012",
  "favorited" : false,
  "full_text" : "this is a test tweet",
  "lang" : "ru",
  "in_reply_to_screen_name" : "whatever",
  "in_reply_to_user_id_str" : "3748274"
}
    """
    t = Tweet(json.loads(raw), screen_name='whatever')
    assert t.permalink is not None
    assert t.dt == datetime(year=2012, month=8, day=30, hour=7, minute=12, second=48, tzinfo=pytz.utc)
    assert t.text == 'this is a test tweet'
    assert t.tid  == '2328934829084'
    assert t.entities is not None
