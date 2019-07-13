#!/usr/bin/env python3
from datetime import date, datetime
from typing import Union, List, Dict, Set
from pathlib import Path
import json

import zipfile

from kython import make_dict

KARLICOSS_ID = '119756204'
DB_PATH = Path('/L/zzz_syncthing/data/tweets')
EXPORTS_PATH = Path('/L/backups/twitter-exports')


import sys
sys.path.append('/L/coding/twidump')
import twidump # type: ignore
sys.path.pop() # TODO not sure if necessary?

Tid = str

# TODO make sure it's not used anywhere else and simplify interface
class Tweet:
    def __init__(self, tw):
        self.tw = tw

    def __getattr__(self, attr):
        return getattr(self.tw, attr)

    @property
    def url(self) -> str:
        from twidump.render.tools import make_tweet_permalink # type: ignore
        return make_tweet_permalink(self.tw.id_str)

    @property
    def time(self) -> str:
        return self.tw.created_at

    @property
    def dt(self) -> datetime:
        return self.tw.get_utc_datetime()

    @property
    def text(self) -> str:
        return self.tw.text

    @property
    def tid(self) -> Tid:
        return self.tw.id_str

    def __str__(self) -> str:
        return str(self.tw)

    def __repr__(self) -> str:
        return repr(self.tw)


def _twidump() -> List[Tweet]:
    import twidump
    # add current package to path to discover config?... nah, twidump should be capable of that.
    from twidump.data_manipulation.timelines import TimelineLoader # type: ignore
    from twidump.component import get_app_injector # type: ignore
    tl_loader = get_app_injector(db_path=DB_PATH).get(TimelineLoader)  # type: TimelineLoader
    tl = tl_loader.load_timeline(KARLICOSS_ID)
    return [Tweet(x) for x in tl]


def _json() -> List[Tweet]:
    from twidump.data.tweet import Tweet as TDTweet # type: ignore

    zips = EXPORTS_PATH.glob('*.zip')
    last = list(sorted(zips, key=lambda p: p.stat().st_mtime))[-1]
    ddd = zipfile.ZipFile(last).read('tweet.js').decode('utf8')
    start = ddd.index('[')
    ddd = ddd[start:]
    tws = []
    for j in json.loads(ddd):
        j['user'] = {} # TODO is it ok?
        tw = Tweet(TDTweet.from_api_dict(j))
        tws.append(tw)
    return tws


def tweets_all() -> List[Tweet]:
    tjson: Dict[Tid, Tweet] = make_dict(_json(), key=lambda t: t.tid)
    tdump: Dict[Tid, Tweet] = make_dict(_twidump(), key=lambda t: t.tid)
    keys: Set[Tid] = set(tdump.keys()).union(set(tjson.keys()))

    # TODO hmm. looks like json generally got longer tweets?
    res: List[Tweet] = []
    for tid in keys:
        if tid in tjson:
            tw = tjson[tid]
        else:
            tw = tdump[tid]
        res.append(tw)
    res.sort(key=lambda t: t.dt)
    return res


def predicate(p) -> List[Tweet]:
    return [t for t in tweets_all() if p(t)]

def predicate_date(p) -> List[Tweet]:
    return predicate(lambda t: p(t.dt.date()))

Datish = Union[date, str]
def tweets_on(*dts: Datish) -> List[Tweet]:
    from kython import parse_date_new
    # TODO how to make sure we don't miss on 29 feb?
    dates = {parse_date_new(d) for d in dts}
    return predicate_date(lambda d: d in dates)

on = tweets_on

def test_on():
    tww = tweets_on('2019-05-11')
    assert len(tww) == 2

def test_all():
    tall = tweets_all()
    assert len(tall) > 100

if __name__ == '__main__':
    for t in tweets_all():
        print(t)
