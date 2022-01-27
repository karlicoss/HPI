'''
Simple location provider, serving as a fallback when more detailed data isn't available
'''
from dataclasses import dataclass
from datetime import datetime, date, time, timezone
from functools import lru_cache
from typing import Sequence, Tuple, Union, cast

from my.config import location as user_config


DateIsh = Union[datetime, date, str]

# todo hopefully reasonable? might be nice to add name or something too
LatLon = Tuple[float, float]

@dataclass
class Config(user_config):
    home: Union[
        LatLon,         # either single, 'current' location
        Sequence[Tuple[ # or, a sequence of location history
            DateIsh,    # date when you moved to
            LatLon,     # the location
        ]]
    ]
    # TODO could make current Optional and somehow determine from system settings?
    @property
    def _history(self) -> Sequence[Tuple[datetime, LatLon]]:
        home1 = self.home
        # todo ugh, can't test for isnstance LatLon, it's a tuple itself
        home2: Sequence[Tuple[DateIsh, LatLon]]
        if isinstance(home1[0], tuple):
            # already a sequence
            home2 = cast(Sequence[Tuple[DateIsh, LatLon]], home1)
        else:
            # must be a pair of coordinates. also doesn't really matter which date to pick?
            loc = cast(LatLon, home1)
            home2 = [(datetime.min, loc)]

        # todo cache?
        res = []
        for x, loc in home2:
            dt: datetime
            if isinstance(x, str):
                dt = datetime.fromisoformat(x)
            elif isinstance(x, datetime):
                dt = x
            else:
                dt = datetime.combine(x, time.min)
            # todo not sure about doing it here, but makes it easier to compare..
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            res.append((dt, loc))
        res = list(sorted(res, key=lambda p: p[0]))
        return res


from ..core.cfg import make_config
config = make_config(Config)


@lru_cache(maxsize=None)
def get_location(dt: datetime) -> LatLon:
    '''
    Interpolates the location at dt
    '''
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    hist = list(reversed(config._history))
    for pdt, loc in hist:
        if dt >= pdt:
            return loc
    else:
        # I guess the most reasonable is to fallback on the first location
        return hist[-1][1]
