from datetime import date, datetime
from typing import Union, Tuple, Optional
from dataclasses import dataclass

from my.core import __NOT_HPI_MODULE__

DateIsh = Union[datetime, date, str]

LatLon = Tuple[float, float]


# TODO: add timezone to this? can use timezonefinder in tz provider instead though

# converted from namedtuple to a dataclass so datasource field can be added optionally
# if we want, can eventually be converted back to a namedtuple when all datasources are compliant
@dataclass
class Location:
    lat: float
    lon: float
    dt: datetime
    accuracy: Optional[float]
    elevation: Optional[float]
    datasource: Optional[str] = None  # which module provided this, useful for debugging
