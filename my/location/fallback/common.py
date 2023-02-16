from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Callable, Sequence, Iterator, List, Union
from datetime import datetime, timedelta

from ..common import LocationProtocol, Location
DateIshExact = Union[datetime, float, int]

@dataclass
class FallbackLocation(LocationProtocol):
    lat: float
    lon: float
    dt: datetime
    duration: Optional[float] = None # time in seconds for how long this is valid
    accuracy: Optional[float] = None
    elevation: Optional[float] = None
    datasource: Optional[str] = None  # which module provided this, useful for debugging

    def to_location(self, end: bool = False) -> Location:
        '''
        by default the start date is used for the location
        If end is True, the start date + duration is used
        '''
        dt: datetime = self.dt
        if end and self.duration is not None:
            dt += timedelta(self.duration)
        return Location(
            lat=self.lat,
            lon=self.lon,
            dt=dt,
            accuracy=self.accuracy,
            elevation=self.elevation,
            datasource=self.datasource,
        )

    @classmethod
    def from_end_date(
        cls,
        lat: float,
        lon: float,
        dt: datetime,
        end_dt: datetime,
        accuracy: Optional[float] = None,
        elevation: Optional[float] = None,
        datasource: Optional[str] = None,
    ) -> FallbackLocation:
        '''
        Create FallbackLocation from a start date and an end date
        '''
        if end_dt < dt:
            raise ValueError("end_date must be after dt")
        duration = (end_dt - dt).total_seconds()
        return cls(
            lat=lat,
            lon=lon,
            dt=dt,
            duration=duration,
            accuracy=accuracy,
            elevation=elevation,
            datasource=datasource,
        )


LocationEstimator = Callable[[DateIshExact], Optional[FallbackLocation]]
LocationEstimators = Sequence[LocationEstimator]

# helper function, instead of dealing with datetimes while comparing, just use epoch timestamps
def _datetime_timestamp(dt: DateIshExact) -> float:
    if isinstance(dt, datetime):
        return dt.timestamp()
    return float(dt)

def _iter_estimate_from(
    dt: DateIshExact,
    estimators: LocationEstimators,
) -> Iterator[FallbackLocation]:
    for est in estimators:
        loc = est(dt)
        if loc is None:
            continue
        yield loc


def estimate_from(
    dt: DateIshExact,
    estimators: LocationEstimators,
    *,
    first_match: bool = False,
    under_accuracy: Optional[int] = None,
) -> Optional[FallbackLocation]:
    '''
    first_match: if True, return the first location found
    under_accuracy: if set, only return locations with accuracy under this value
    '''
    found: List[FallbackLocation] = []
    for loc in _iter_estimate_from(dt, estimators):
        if under_accuracy is not None and loc.accuracy is not None and loc.accuracy > under_accuracy:
            continue
        if first_match:
            return loc
        found.append(loc)

    if not found:
        return None

    # if all items have accuracy, return the one with the lowest accuracy
    # otherwise, we should prefer the order that the estimators are passed in as
    if all(loc.accuracy is not None for loc in found):
        # return the location with the lowest accuracy
        return min(has_accuracy, key=lambda loc: loc.accuracy)  # type: ignore[union-attr]
    else:
        # return the first location
        return found[0]
