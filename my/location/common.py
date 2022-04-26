from datetime import date, datetime
from typing import Union, Tuple, NamedTuple, Optional

from my.core import __NOT_HPI_MODULE__

DateIsh = Union[datetime, date, str]

LatLon = Tuple[float, float]


# TODO: add timezone to this? can use timezonefinder in tz provider instead though
class Location(NamedTuple):
    lat: float
    lon: float
    dt: datetime
    accuracy: Optional[float]
    elevation: Optional[float]
