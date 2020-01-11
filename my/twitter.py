"""
Uses official twitter archive export

See https://help.twitter.com/en/managing-your-account/how-to-download-your-twitter-archive

Expects path to be set
- via ~configure~ (before calling anything else)
- or in ~mycfg.twitter.export_path~
"""


from datetime import date, datetime
from typing import Union, List, Dict, Set, Optional, Iterator, Any, NamedTuple
from pathlib import Path
import json
import zipfile

import pytz

from .common import PathIsh, get_files, LazyLogger


logger = LazyLogger('my.twitter')


_export_path: Optional[Path] = None
def configure(*, export_path: Optional[PathIsh]=None) -> None:
    if export_path is not None:
        global _export_path
        _export_path = Path(export_path)


def _get_export() -> Path:
    export_path = _export_path
    if export_path is None:
        # fallback to mycfg
        from mycfg import paths
        export_path = paths.twitter.export_path
    return max(get_files(export_path, '*.zip'))


Tid = str


# TODO a bit messy... perhaps we do need DAL for twitter exports
Json = Dict[str, Any]


# TODO make sure it's not used anywhere else and simplify interface
class Tweet(NamedTuple):
    raw: Json

    @property
    def tid(self) -> Tid:
        return self.raw['id_str']

    @property
    def permalink(self) -> str:
        return f'https://twitter.com/i/web/status/{self.tid}'

    @property
    def dt(self) -> datetime:
        dts = self.raw['created_at']
        return datetime.strptime(dts, '%a %b %d %H:%M:%S %z %Y')

    @property
    def text(self) -> str:
        return self.raw['full_text']

    @property
    def entities(self):
        return self.raw['entities']

    def __str__(self) -> str:
        return str(self.raw)

    def __repr__(self) -> str:
        return repr(self.raw)


class Like(NamedTuple):
    raw: Json

    @property
    def tid(self) -> Tid:
        return self.raw['tweetId']

    @property
    def text(self) -> str:
        return self.raw['fullText']


class ZipExport:
    def __init__(self) -> None:
        pass

    def raw(self, what: str): # TODO Json in common?
        epath = _get_export()
        logger.info('processing: %s %s', epath, what)
        ddd = zipfile.ZipFile(epath).read(what).decode('utf8')
        start = ddd.index('[')
        ddd = ddd[start:]
        for j in json.loads(ddd):
            yield j


    def tweets(self) -> Iterator[Tweet]:
        for r in self.raw('tweet.js'):
            yield Tweet(r)


    def likes(self) -> Iterator[Like]:
        # TODO ugh. would be nice to unify Tweet/Like interface
        # however, akeout only got tweetId, full text and url
        for r in self.raw('like.js'):
            yield Like(r)


def tweets_all() -> List[Tweet]:
    return list(sorted(ZipExport().tweets(), key=lambda t: t.dt))


def likes_all() -> List[Like]:
    return list(ZipExport().likes())


def predicate(p) -> List[Tweet]:
    return [t for t in tweets_all() if p(t)]


def predicate_date(p) -> List[Tweet]:
    return predicate(lambda t: p(t.dt.date()))

# TODO move these to private tests?
Datish = Union[date, str]
def tweets_on(*dts: Datish) -> List[Tweet]:
    from kython import parse_date_new
    # TODO how to make sure we don't miss on 29 feb?
    dates = {parse_date_new(d) for d in dts}
    return predicate_date(lambda d: d in dates)

on = tweets_on


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
    t = Tweet(json.loads(raw))
    assert t.permalink is not None
    assert t.dt == datetime(year=2012, month=8, day=30, hour=7, minute=12, second=48, tzinfo=pytz.utc)
    assert t.text == 'this is a test tweet'
    assert t.tid  == '2328934829084'
    assert t.entities is not None
