from datetime import date, datetime
from typing import Union, List

KARLICOSS_ID = '119756204'

# TODO how to discover configs? ... I guess symlinking...
def tweets_all():
    import sys
    sys.path.append("/L/coding/twidump")
    import twidump
    # add current package to path to discover config?... nah, twidump should be capable of that. 
    from twidump.data_manipulation.timelines import TimelineLoader
    from twidump.component import get_app_injector
    tl_loader = get_app_injector().get(TimelineLoader)  # type: TimelineLoader
    tl = tl_loader.load_timeline(KARLICOSS_ID)
    return tl


class Tweet:
    def __init__(self, tw):
        self.tw = tw

    def __getattr__(self, attr):
        return getattr(self.tw, attr)

    @property
    def url(self) -> str:
        from twidump.render.tools import make_tweet_permalink
        return make_tweet_permalink(self.tw.id_str)

    @property
    def time(self) -> str:
        return self.tw.created_at

    @property
    def datetime(self) -> datetime:
        return self.tw.get_utc_datetime()

    def __str__(self) -> str:
        return str(self.tw)

    def __repr__(self) -> str:
        return repr(self.tw)

def predicate(p) -> List[Tweet]:
    return [Tweet(t) for t in tweets_all() if p(t)]

def predicate_date(p) -> List[Tweet]:
    return predicate(lambda t: p(t.get_utc_datetime().date()))

Datish = Union[date, str]
def tweets_on(*dts: Datish) -> List[Tweet]:
    from kython import parse_date_new
    # TODO how to make sure we don't miss on 29 feb?
    dates = {parse_date_new(d) for d in dts}
    return predicate_date(lambda d: d in dates)

on = tweets_on
