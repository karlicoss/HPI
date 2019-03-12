from datetime import date, datetime
from typing import Union, List
from pathlib import Path

KARLICOSS_ID = '119756204'
DB_PATH = Path('/L/zzz_syncthing/data/tweets')


import sys
sys.path.append('/L/Dropbox/coding/twidump')
import twidump # type: ignore
sys.path.pop() # TODO not sure if necessary?

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
    def tid(self) -> str:
        return self.tw.id_str

    def __str__(self) -> str:
        return str(self.tw)

    def __repr__(self) -> str:
        return repr(self.tw)

def tweets_all():
    import twidump
    # add current package to path to discover config?... nah, twidump should be capable of that.
    from twidump.data_manipulation.timelines import TimelineLoader # type: ignore
    from twidump.component import get_app_injector # type: ignore
    tl_loader = get_app_injector(db_path=DB_PATH).get(TimelineLoader)  # type: TimelineLoader
    tl = tl_loader.load_timeline(KARLICOSS_ID)
    return [Tweet(x) for x in tl]


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

if __name__ == '__main__':
    for t in tweets_all():
        print(t)
