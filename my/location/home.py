'''
Simple location provider, serving as a fallback when more detailed data isn't available
'''
from dataclasses import dataclass
from datetime import datetime, date
from functools import lru_cache
from typing import Optional, Sequence, Tuple, Union

from ..core.common import fromisoformat

from my.config import location as L
user_config = L.home


DateIsh = Union[datetime, str]

# todo hopefully reasonable? might be nice to add name or something too
LatLon = Tuple[float, float]

@dataclass
class home(user_config):
    # TODO could make current Optional and somehow determine from system settings?
    # todo possibly also could be core config.. but not sure
    current: LatLon

    '''
    First element is location, the second is the date when you left it (datetime/ISO string)
    '''
    past: Sequence[Tuple[LatLon, DateIsh]] = ()
    # todo test for proper localized/not localized handling as well
    # todo make sure they are increasing


    @property
    def _past(self) -> Sequence[Tuple[LatLon, datetime]]:
        # todo cache?
        res = []
        for loc, x in self.past:
            dt: datetime
            if isinstance(x, str):
                dt = fromisoformat(x)
            else:
                dt = x
            res.append((loc, dt))
        return res

        

from ..core.cfg import make_config
config = make_config(home)


@lru_cache(maxsize=None)
def get_location(dt: datetime) -> LatLon:
    '''
    Interpolates the location at dt
    '''
    for loc, pdt in config._past:
        if dt <= pdt:
            return loc
    return config.current
